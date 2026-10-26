
-- BooksVault: Optional demonstration data
-- Run after schema.sql.
-- These examples are only for a fresh/demo database.

INSERT INTO bookshop.customer
    (customer_id, cust_name, cust_phone, cust_email, cust_addr)
VALUES
    (1, 'Aarav Sharma', '9876543210',
     'aarav@example.com', 'Nanded'),
    (2, 'Ananya Patil', '9876501234',
     'ananya@example.com', 'Pune')
ON CONFLICT (customer_id) DO NOTHING;

INSERT INTO bookshop.dealer
    (dealer_id, deal_name, deal_phone, deal_email, deal_addr)
VALUES
    (1, 'Readers Wholesale', '9123456780',
     'readers@example.com', 'Mumbai'),
    (2, 'Classic Book Distributors', '9234567890',
     'classic@example.com', 'Pune')
ON CONFLICT (dealer_id) DO NOTHING;

INSERT INTO bookshop.book
    (isbn_id, title, genre, price, stock, author_nm, publisher_nm)
VALUES
    (9780000000001, 'The Silent Garden', 'Fiction',
     299.00, 15, 'A. Sharma', 'Readers Press'),
    (9780000000002, 'Learning PostgreSQL', 'Technology',
     499.00, 10, 'R. Mehta', 'Tech Books'),
    (9780000000003, 'The Art of Reading', 'Education',
     199.00, 20, 'S. Kulkarni', 'Classic Press')
ON CONFLICT (isbn_id) DO NOTHING;

INSERT INTO bookshop.book_supplier (isbn_id, dealer_id)
VALUES
    (9780000000001, 1),
    (9780000000002, 2),
    (9780000000003, 1)
ON CONFLICT (isbn_id, dealer_id) DO NOTHING;
