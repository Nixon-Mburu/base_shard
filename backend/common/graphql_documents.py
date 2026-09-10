MERCHANT = "id businessName owner type city phone address point { lat lng }"
PRODUCT = "id name category unit price stock icon tag color"
QUOTE = "items { " + PRODUCT + " quantity } subtotal delivery total count currency"
ORDER = (
    "id merchant { "
    + MERCHANT
    + " } method status error createdAt paymentSimulated deliveryStatus "
    + QUOTE
)
DOCUMENTS = {
    "me": "query Me { me { " + MERCHANT + " } }",
    "products": "query Products { products { " + PRODUCT + " } }",
    "quote": "query Quote($input: BasketInput!) { quote(input: $input) { " + QUOTE + " } }",
    "orders": "query Orders($limit: Int) { orders(limit: $limit) { " + ORDER + " } }",
    "order": "query Order($id: ID!) { order(id: $id) { " + ORDER + " } }",
    "createMerchant": "mutation CreateMerchant($input: MerchantInput!) { createMerchant(input: $input) { token merchant { "
    + MERCHANT
    + " } } }",
    "updateMerchant": "mutation UpdateMerchant($input: MerchantInput!) { updateMerchant(input: $input) { "
    + MERCHANT
    + " } }",
    "placeOrder": "mutation PlaceOrder($input: OrderInput!, $idempotencyKey: ID!) { placeOrder(input: $input, idempotencyKey: $idempotencyKey) { "
    + ORDER
    + " } }",
    "allocateStock": "mutation AllocateStock($input: AllocationInput!, $id: ID!) { allocateStock(input: $input, id: $id) { "
    + QUOTE
    + " } }",
}
