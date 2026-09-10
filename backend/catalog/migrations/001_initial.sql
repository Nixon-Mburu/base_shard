CREATE TABLE products (
 id TEXT PRIMARY KEY,
 data JSONB NOT NULL,
 price INTEGER NOT NULL CHECK (price >= 0),
 stock INTEGER NOT NULL CHECK (stock >= 0)
);
CREATE TABLE allocations (
 id UUID PRIMARY KEY,
 request JSONB NOT NULL,
 result JSONB NOT NULL,
 created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
