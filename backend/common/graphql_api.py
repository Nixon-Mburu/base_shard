"""Typed GraphQL transport shared by the independently deployed services."""

import logging

import psycopg
from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse
from graphql import GraphQLError, build_schema, execute_sync, parse, validate
from graphql.language import FieldNode, FragmentSpreadNode
from pydantic import ValidationError

TYPES = """
type Point { lat: Float!, lng: Float! }
input PointInput { lat: Float!, lng: Float! }
type Merchant { id: ID!, businessName: String!, owner: String!, type: String!, city: String!, phone: String!, address: String!, point: Point! }
input MerchantInput { businessName: String!, owner: String!, type: String!, city: String!, phone: String!, address: String!, point: PointInput! }
type MerchantSession { merchant: Merchant!, token: String! }
type Product { id: ID!, name: String!, category: String!, unit: String!, price: Int!, stock: Int!, icon: String, tag: String, color: String }
type OrderItem { id: ID!, name: String!, category: String!, unit: String!, price: Int!, stock: Int!, icon: String, tag: String, color: String, quantity: Int! }
input ItemInput { id: ID!, quantity: Int! }
input BasketInput { items: [ItemInput!]! }
input AllocationInput { items: [ItemInput!]!, expectedTotal: Int! }
input OrderInput { items: [ItemInput!]!, expectedTotal: Int!, method: String!, outcome: String = "success" }
type Quote { items: [OrderItem!]!, subtotal: Int!, delivery: Int!, total: Int!, count: Int!, currency: String! }
type Order { id: ID!, merchant: Merchant!, method: String!, status: String!, error: String, createdAt: String!, paymentSimulated: Boolean!, deliveryStatus: String!, items: [OrderItem!]!, subtotal: Int, delivery: Int, total: Int, count: Int, currency: String }
"""
QUERIES = {
    "me": "me: Merchant",
    "products": "products: [Product!]",
    "quote": "quote(input: BasketInput!): Quote",
    "orders": "orders(limit: Int = 30): [Order!]",
    "order": "order(id: ID!): Order",
}
MUTATIONS = {
    "createMerchant": "createMerchant(input: MerchantInput!): MerchantSession",
    "updateMerchant": "updateMerchant(input: MerchantInput!): Merchant",
    "placeOrder": "placeOrder(input: OrderInput!, idempotencyKey: ID!): Order",
    "allocateStock": "allocateStock(input: AllocationInput!, id: ID!): Quote",
}


def safe_error(error):
    cause = error.original_error
    if isinstance(cause, HTTPException):
        status, message = cause.status_code, str(cause.detail)
    elif isinstance(cause, (ValidationError, ValueError)):
        status, message = 422, "Invalid input values"
    elif isinstance(cause, psycopg.Error):
        status, message = 503, "Database temporarily unavailable. Please retry."
    elif cause is not None:
        logging.getLogger("base_grid").error("GraphQL resolver failed: %s", type(cause).__name__)
        status, message = 500, "Internal service error"
    else:
        status, message = 400, error.message
    codes = {
        401: "UNAUTHENTICATED",
        403: "FORBIDDEN",
        404: "NOT_FOUND",
        409: "CONFLICT",
        422: "BAD_USER_INPUT",
        503: "SERVICE_UNAVAILABLE",
    }
    return {
        "message": message,
        "path": error.path,
        "extensions": {
            "status": status,
            "code": codes.get(status, "BAD_REQUEST" if status == 400 else "INTERNAL_SERVER_ERROR"),
        },
    }


def mount(app, queries, mutations=None, path="/graphql", authorize=None):
    mutations = mutations or {}
    schema = build_schema(
        TYPES
        + "type Query { "
        + " ".join(QUERIES[k] for k in queries)
        + (" _service: String" if not queries else "")
        + " }"
        + (
            "type Mutation { " + " ".join(MUTATIONS[k] for k in mutations) + " }"
            if mutations
            else ""
        )
    )
    for kind, resolvers in (("Query", queries), ("Mutation", mutations)):
        for name, resolver in resolvers.items():
            schema.get_type(kind).fields[name].resolve = resolver

    @app.post(path)
    def graphql_endpoint(body: dict, request: Request):
        request.scope["graphql.operation"] = "invalid"
        request.scope["graphql.outcome"] = "error"
        try:
            if authorize:
                authorize(request)
            query = body.get("query")
            if not isinstance(query, str) or len(query) > 32768:
                raise GraphQLError("Provide a query of at most 32768 characters")
            variables = body.get("variables")
            if variables is not None and not isinstance(variables, dict):
                raise GraphQLError("Variables must be an object")
            document = parse(query, max_tokens=2000)
            errors = validate(schema, document)
            if errors:
                return JSONResponse({"errors": [safe_error(e) for e in errors]}, status_code=400)
            fragments = {
                d.name.value: d for d in document.definitions if d.kind == "fragment_definition"
            }

            def fields(selection, depth=0):
                if depth > 12:
                    raise GraphQLError("Query depth exceeds 12")
                count = 0
                for node in selection.selections:
                    if isinstance(node, FragmentSpreadNode):
                        count += fields(fragments[node.name.value].selection_set, depth + 1)
                    else:
                        count += 1
                        if node.selection_set:
                            count += fields(node.selection_set, depth + 1)
                return count

            operations = [d for d in document.definitions if d.kind == "operation_definition"]
            for operation in operations:
                if fields(operation.selection_set) > 500:
                    raise GraphQLError("Query exceeds field budget")
            selected = [
                o
                for o in operations
                if not body.get("operationName")
                or (o.name and o.name.value == body["operationName"])
            ]
            if len(selected) == 1:
                nodes = selected[0].selection_set.selections
                label = (
                    nodes[0].name.value
                    if len(nodes) == 1 and isinstance(nodes[0], FieldNode)
                    else "multiple"
                )
                request.scope["graphql.operation"] = (
                    label if label in queries or label in mutations else "introspection"
                )
            result = execute_sync(
                schema,
                document,
                context_value=request,
                variable_values=variables,
                operation_name=body.get("operationName"),
            )
            request.scope["graphql.outcome"] = "error" if result.errors else "success"
            return JSONResponse(
                {
                    "data": result.data,
                    **({"errors": [safe_error(e) for e in result.errors]} if result.errors else {}),
                }
            )
        except (GraphQLError, HTTPException) as exc:
            error = (
                exc
                if isinstance(exc, GraphQLError)
                else GraphQLError(str(exc.detail), original_error=exc)
            )
            return JSONResponse(
                {"errors": [safe_error(error)]},
                status_code=exc.status_code if isinstance(exc, HTTPException) else 400,
            )

    return schema


def allocation_input(value):
    return {
        **{k: v for k, v in value.items() if k != "expectedTotal"},
        "expected_total": value["expectedTotal"],
    }
