CREATE TABLE orders (
 id UUID PRIMARY KEY,
 merchant_id UUID NOT NULL,
 merchant JSONB NOT NULL,
 idempotency_key UUID NOT NULL,
 request JSONB NOT NULL,
 status TEXT NOT NULL CHECK (status IN ('pending','confirmed','declined','rejected')),
 summary JSONB,
 error TEXT,
 created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
 updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
 UNIQUE(merchant_id, idempotency_key)
);
CREATE INDEX orders_merchant_created ON orders(merchant_id, created_at DESC);
CREATE INDEX orders_pending ON orders(created_at) WHERE status='pending';
