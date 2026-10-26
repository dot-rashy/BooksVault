import re
import os
from decimal import Decimal, InvalidOperation

import psycopg
from dotenv import load_dotenv
from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    flash,
)

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "books-vault-local-key")


def get_db_connection():
    return psycopg.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", "5432")),
        dbname=os.getenv("DB_NAME", "bookshop_db"),
        user=os.getenv("DB_USER", "postgres"),
        password=os.getenv("DB_PASSWORD"),
    )


def validate_book_form():
    """Validate the book form and return cleaned data or an error."""
    isbn_id = request.form.get("isbn_id", "").strip()
    title = request.form.get("title", "").strip()
    author_nm = request.form.get("author_nm", "").strip() or None
    publisher_nm = request.form.get("publisher_nm", "").strip() or None
    genre = request.form.get("genre", "").strip() or None
    price_text = request.form.get("price", "").strip()
    stock_text = request.form.get("stock", "").strip()

    if not title:
        return None, "Book title is required."

    if len(title) > 255:
        return None, "Book title is too long."

    try:
        price = Decimal(price_text)
        if not price.is_finite() or price < 0:
            raise InvalidOperation
        if price.as_tuple().exponent < -2:
            return None, "Price can have at most two decimal places."
    except (InvalidOperation, ValueError):
        return None, "Enter a valid price (e.g. 299.00)."

    try:
        stock = int(stock_text)
        if stock < 0:
            return None, "Stock cannot be negative."
    except (ValueError, TypeError):
        return None, "Enter a valid whole number for stock."

    if len(author_nm or "") > 255 or len(publisher_nm or "") > 255:
        return None, "Author or publisher name is too long."

    if len(genre or "") > 255:
        return None, "Genre is too long."

    data = {
        "title": title,
        "author_nm": author_nm,
        "publisher_nm": publisher_nm,
        "genre": genre,
        "price": price,
        "stock": stock,
    }

    if isbn_id:
        try:
            parsed_isbn = int(isbn_id)
            if parsed_isbn <= 0:
                raise ValueError
            data["isbn_id"] = parsed_isbn
        except ValueError:
            return None, "ISBN/ID must be a positive whole number."

    return data, None


@app.route("/")
def home():
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM bookshop.book")
            total_books = cur.fetchone()[0]

            cur.execute("SELECT COUNT(*) FROM bookshop.customer")
            total_customers = cur.fetchone()[0]

            cur.execute("SELECT COUNT(*) FROM bookshop.orders")
            total_orders = cur.fetchone()[0]

            cur.execute("""
                SELECT COUNT(*)
                FROM bookshop.book
                WHERE stock <= 5
            """)
            low_stock = cur.fetchone()[0]

            cur.execute("""
                SELECT isbn_id, title, author_nm, genre, price, stock
                FROM bookshop.book
                ORDER BY title
                LIMIT 8
            """)
            books = cur.fetchall()

    return render_template(
        "index.html",
        total_books=total_books,
        total_customers=total_customers,
        total_orders=total_orders,
        low_stock=low_stock,
        books=books,
    )


@app.route("/books")
def books_page():
    search = request.args.get("search", "").strip()

    with get_db_connection() as conn:
        with conn.cursor() as cur:
            if search:
                cur.execute("""
                    SELECT isbn_id, title, author_nm, genre, price, stock
                    FROM bookshop.book
                    WHERE title ILIKE %s
                       OR COALESCE(author_nm, '') ILIKE %s
                       OR COALESCE(genre, '') ILIKE %s
                    ORDER BY title
                """, (f"%{search}%", f"%{search}%", f"%{search}%"))
            else:
                cur.execute("""
                    SELECT isbn_id, title, author_nm, genre, price, stock
                    FROM bookshop.book
                    ORDER BY title
                """)

            books = cur.fetchall()

    return render_template("books.html", books=books, search=search)


@app.route("/books/add", methods=["GET", "POST"])
def add_book():
    if request.method == "POST":
        data, error = validate_book_form()

        if error:
            flash(error, "error")
            return render_template("book_form.html", book=request.form, mode="add")

        # ISBN/ID is required by your schema, so the user supplies it.
        if "isbn_id" not in data:
            flash("ISBN/ID is required.", "error")
            return render_template("book_form.html", book=request.form, mode="add")

        try:
            with get_db_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        INSERT INTO bookshop.book
                            (isbn_id, title, author_nm, publisher_nm,
                             genre, price, stock)
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """, (
                        data["isbn_id"],
                        data["title"],
                        data["author_nm"],
                        data["publisher_nm"],
                        data["genre"],
                        data["price"],
                        data["stock"],
                    ))

            flash("Book added successfully!", "success")
            return redirect(url_for("books_page"))

        except psycopg.errors.UniqueViolation:
            flash("That ISBN/ID already exists. Please use a different one.", "error")
        except psycopg.Error:
            app.logger.exception("Could not add book")
            flash("The book could not be added. Check the database fields and try again.", "error")

        return render_template("book_form.html", book=request.form, mode="add")

    return render_template("book_form.html", book={}, mode="add")


@app.route("/books/edit/<int:isbn_id>", methods=["GET", "POST"])
def edit_book(isbn_id):
    if request.method == "POST":
        data, error = validate_book_form()

        if error:
            flash(error, "error")
            return render_template(
                "book_form.html", book=request.form, mode="edit"
            )

        try:
            with get_db_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        UPDATE bookshop.book
                        SET title = %s,
                            author_nm = %s,
                            publisher_nm = %s,
                            genre = %s,
                            price = %s,
                            stock = %s
                        WHERE isbn_id = %s
                    """, (
                        data["title"],
                        data["author_nm"],
                        data["publisher_nm"],
                        data["genre"],
                        data["price"],
                        data["stock"],
                        isbn_id,
                    ))

                    if cur.rowcount == 0:
                        flash("Book not found.", "error")
                        return redirect(url_for("books_page"))

            flash("Book updated successfully!", "success")
            return redirect(url_for("books_page"))

        except psycopg.Error:
            app.logger.exception("Could not update book")
            flash("The book could not be updated. Please try again.", "error")
            return render_template(
                "book_form.html", book=request.form, mode="edit"
            )

    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT isbn_id, title, author_nm, publisher_nm,
                       genre, price, stock
                FROM bookshop.book
                WHERE isbn_id = %s
            """, (isbn_id,))
            row = cur.fetchone()

    if row is None:
        flash("Book not found.", "error")
        return redirect(url_for("books_page"))

    book = {
        "isbn_id": row[0],
        "title": row[1],
        "author_nm": row[2] or "",
        "publisher_nm": row[3] or "",
        "genre": row[4] or "",
        "price": row[5],
        "stock": row[6],
    }

    return render_template("book_form.html", book=book, mode="edit")


@app.route("/books/delete/<int:isbn_id>", methods=["POST"])
def delete_book(isbn_id):
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                # Protect books that are used by supplier or order records.
                cur.execute("""
                    SELECT EXISTS (
                        SELECT 1 FROM bookshop.book_supplier
                        WHERE isbn_id = %s
                    ) OR EXISTS (
                        SELECT 1 FROM bookshop.order_books
                        WHERE isbn_id = %s
                    )
                """, (isbn_id, isbn_id))

                is_referenced = cur.fetchone()[0]

                if is_referenced:
                    flash(
                        "This book is linked to supplier or order records "
                        "and cannot be deleted.",
                        "error",
                    )
                    return redirect(url_for("books_page"))

                cur.execute(
                    "DELETE FROM bookshop.book WHERE isbn_id = %s",
                    (isbn_id,),
                )

                if cur.rowcount == 0:
                    flash("Book not found.", "error")
                else:
                    flash("Book deleted successfully.", "success")

    except psycopg.Error:
        app.logger.exception("Could not delete book")
        flash("The book could not be deleted. Please try again.", "error")

    return redirect(url_for("books_page"))


# ---------------- CUSTOMER MANAGEMENT ----------------

@app.route("/customers")
def customers_page():
    search = request.args.get("search", "").strip()

    with get_db_connection() as conn:
        with conn.cursor() as cur:
            if search:
                pattern = f"%{search}%"
                cur.execute("""
                    SELECT customer_id, cust_name, cust_phone,
                           cust_email, cust_addr
                    FROM bookshop.customer
                    WHERE cust_name ILIKE %s
                       OR COALESCE(cust_phone, '') ILIKE %s
                       OR COALESCE(cust_email, '') ILIKE %s
                    ORDER BY cust_name
                """, (pattern, pattern, pattern))
            else:
                cur.execute("""
                    SELECT customer_id, cust_name, cust_phone,
                           cust_email, cust_addr
                    FROM bookshop.customer
                    ORDER BY cust_name
                """)

            customers = cur.fetchall()

    return render_template(
        "customers.html",
        customers=customers,
        search=search
    )


@app.route("/customers/add", methods=["GET", "POST"])
def add_customer():
    if request.method == "POST":
        name = request.form.get("cust_name", "").strip()
        phone = request.form.get("cust_phone", "").strip() or None
        email = request.form.get("cust_email", "").strip().lower() or None
        address = request.form.get("cust_addr", "").strip() or None

        customer_data = {
            "cust_name": name,
            "cust_phone": phone or "",
            "cust_email": email or "",
            "cust_addr": address or "",
        }

        if not name:
            flash("Customer name is required.", "error")
            return render_template(
                "customer_form.html",
                customer=customer_data,
                mode="add"
            )

        if len(name) > 100 or len(phone or "") > 20 or len(email or "") > 150:
            flash("One or more fields exceed the allowed length.", "error")
            return render_template(
                "customer_form.html",
                customer=customer_data,
                mode="add"
            )

        if email and not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
            flash("Please enter a valid email address.", "error")
            return render_template(
                "customer_form.html",
                customer=customer_data,
                mode="add"
            )

        try:
            with get_db_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        INSERT INTO bookshop.customer
                            (cust_name, cust_phone, cust_email, cust_addr)
                        VALUES (%s, %s, %s, %s)
                    """, (name, phone, email, address))

            flash("Customer added successfully!", "success")
            return redirect(url_for("customers_page"))

        except psycopg.errors.UniqueViolation:
            flash("That email address is already registered.", "error")
        except psycopg.Error:
            app.logger.exception("Could not add customer")
            flash("Could not add customer. Please try again.", "error")

        return render_template(
            "customer_form.html",
            customer=customer_data,
            mode="add"
        )

    return render_template("customer_form.html", customer={}, mode="add")


@app.route("/customers/edit/<int:customer_id>", methods=["GET", "POST"])
def edit_customer(customer_id):
    if request.method == "POST":
        name = request.form.get("cust_name", "").strip()
        phone = request.form.get("cust_phone", "").strip() or None
        email = request.form.get("cust_email", "").strip().lower() or None
        address = request.form.get("cust_addr", "").strip() or None

        customer_data = {
            "customer_id": customer_id,
            "cust_name": name,
            "cust_phone": phone or "",
            "cust_email": email or "",
            "cust_addr": address or "",
        }

        if not name:
            flash("Customer name is required.", "error")
            return render_template(
                "customer_form.html",
                customer=customer_data,
                mode="edit"
            )

        if len(name) > 100 or len(phone or "") > 20 or len(email or "") > 150:
            flash("One or more fields exceed the allowed length.", "error")
            return render_template(
                "customer_form.html",
                customer=customer_data,
                mode="edit"
            )

        if email and not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
            flash("Please enter a valid email address.", "error")
            return render_template(
                "customer_form.html",
                customer=customer_data,
                mode="edit"
            )

        try:
            with get_db_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        UPDATE bookshop.customer
                        SET cust_name = %s,
                            cust_phone = %s,
                            cust_email = %s,
                            cust_addr = %s
                        WHERE customer_id = %s
                    """, (name, phone, email, address, customer_id))

                    if cur.rowcount == 0:
                        flash("Customer not found.", "error")
                        return redirect(url_for("customers_page"))

            flash("Customer updated successfully!", "success")
            return redirect(url_for("customers_page"))

        except psycopg.errors.UniqueViolation:
            flash("That email address is already registered.", "error")
        except psycopg.Error:
            app.logger.exception("Could not update customer")
            flash("Could not update customer. Please try again.", "error")

        return render_template(
            "customer_form.html",
            customer=customer_data,
            mode="edit"
        )

    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT customer_id, cust_name, cust_phone,
                       cust_email, cust_addr
                FROM bookshop.customer
                WHERE customer_id = %s
            """, (customer_id,))
            row = cur.fetchone()

    if row is None:
        flash("Customer not found.", "error")
        return redirect(url_for("customers_page"))

    customer = {
        "customer_id": row[0],
        "cust_name": row[1],
        "cust_phone": row[2] or "",
        "cust_email": row[3] or "",
        "cust_addr": row[4] or "",
    }

    return render_template(
        "customer_form.html",
        customer=customer,
        mode="edit"
    )


@app.route("/customers/delete/<int:customer_id>", methods=["POST"])
def delete_customer(customer_id):
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT EXISTS (
                        SELECT 1
                        FROM bookshop.orders
                        WHERE customer_id = %s
                    )
                """, (customer_id,))

                has_orders = cur.fetchone()[0]

                if has_orders:
                    flash(
                        "This customer has existing orders and cannot be deleted.",
                        "error"
                    )
                    return redirect(url_for("customers_page"))

                cur.execute("""
                    DELETE FROM bookshop.customer
                    WHERE customer_id = %s
                """, (customer_id,))

                if cur.rowcount == 0:
                    flash("Customer not found.", "error")
                else:
                    flash("Customer deleted successfully.", "success")

    except psycopg.Error:
        app.logger.exception("Could not delete customer")
        flash("Could not delete customer. Please try again.", "error")

    return redirect(url_for("customers_page"))
    
@app.route("/dealers")
def dealers_page():
    search = request.args.get("search", "").strip()

    with get_db_connection() as conn:
        with conn.cursor() as cur:
            if search:
                cur.execute("""
                    SELECT dealer_id, deal_name, deal_phone,
                           deal_email, deal_addr
                    FROM bookshop.dealer
                    WHERE deal_name ILIKE %s
                       OR deal_phone ILIKE %s
                       OR deal_email ILIKE %s
                    ORDER BY deal_name
                """, (f"%{search}%", f"%{search}%", f"%{search}%"))
            else:
                cur.execute("""
                    SELECT dealer_id, deal_name, deal_phone,
                           deal_email, deal_addr
                    FROM bookshop.dealer
                    ORDER BY deal_name
                """)

            dealers = cur.fetchall()

    return render_template(
        "dealers.html",
        dealers=dealers,
        search=search
    )


@app.route("/dealers/add", methods=["GET", "POST"])
def add_dealer():
    if request.method == "POST":
        name = request.form.get("deal_name", "").strip()
        phone = request.form.get("deal_phone", "").strip()
        email = request.form.get("deal_email", "").strip() or None
        address = request.form.get("deal_addr", "").strip()

        if not name:
            flash("Dealer name is required.", "error")
            return render_template("dealer_form.html", dealer=None)

        try:
            with get_db_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        INSERT INTO bookshop.dealer
                            (deal_name, deal_phone, deal_email, deal_addr)
                        VALUES (%s, %s, %s, %s)
                    """, (name, phone, email, address))

            flash("Dealer added successfully!", "success")
            return redirect(url_for("dealers_page"))

        except Exception:
            flash("Could not add dealer. Please check the details and try again.", "error")

    return render_template("dealer_form.html", dealer=None)


@app.route("/dealers/edit/<int:dealer_id>", methods=["GET", "POST"])
def edit_dealer(dealer_id):
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT dealer_id, deal_name, deal_phone,
                       deal_email, deal_addr
                FROM bookshop.dealer
                WHERE dealer_id = %s
            """, (dealer_id,))
            dealer = cur.fetchone()

    if dealer is None:
        flash("Dealer not found.", "error")
        return redirect(url_for("dealers_page"))

    if request.method == "POST":
        name = request.form.get("deal_name", "").strip()
        phone = request.form.get("deal_phone", "").strip()
        email = request.form.get("deal_email", "").strip() or None
        address = request.form.get("deal_addr", "").strip()

        if not name:
            flash("Dealer name is required.", "error")
            return render_template("dealer_form.html", dealer=dealer)

        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    UPDATE bookshop.dealer
                    SET deal_name = %s, deal_phone = %s,
                        deal_email = %s, deal_addr = %s
                    WHERE dealer_id = %s
                """, (name, phone, email, address, dealer_id))

        flash("Dealer updated successfully!", "success")
        return redirect(url_for("dealers_page"))

    return render_template("dealer_form.html", dealer=dealer)


@app.route("/dealers/delete/<int:dealer_id>", methods=["POST"])
def delete_dealer(dealer_id):
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT EXISTS (
                    SELECT 1
                    FROM bookshop.book_supplier
                    WHERE dealer_id = %s
                )
            """, (dealer_id,))

            is_supplier = cur.fetchone()[0]

            if is_supplier:
                flash(
                    "Cannot delete this dealer because they supply books.",
                    "error"
                )
            else:
                cur.execute("""
                    DELETE FROM bookshop.dealer
                    WHERE dealer_id = %s
                """, (dealer_id,))

                if cur.rowcount:
                    flash("Dealer deleted successfully!", "success")
                else:
                    flash("Dealer not found.", "error")

    return redirect(url_for("dealers_page"))


@app.route("/orders")
def orders_page():
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT o.order_id, c.cust_name, o.order_date,
                       COALESCE(SUM(ob.quantity * ob.unit_price), 0) AS total
                FROM bookshop.orders o
                JOIN bookshop.customer c
                    ON c.customer_id = o.customer_id
                LEFT JOIN bookshop.order_books ob
                    ON ob.order_id = o.order_id
                GROUP BY o.order_id, c.cust_name, o.order_date
                ORDER BY o.order_date DESC, o.order_id DESC
            """)
            orders = cur.fetchall()

    return render_template("orders.html", orders=orders)


@app.route("/orders/add", methods=["GET", "POST"])
def add_order():
    # Load customers and available books for the order form.
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT customer_id, cust_name
                FROM bookshop.customer
                ORDER BY cust_name
            """)
            customers = cur.fetchall()

            cur.execute("""
                SELECT isbn_id, title, price, stock
                FROM bookshop.book
                WHERE stock > 0
                ORDER BY title
            """)
            books = cur.fetchall()

    if request.method == "POST":
        try:
            customer_id = int(request.form.get("customer_id", ""))

            submitted_isbns = request.form.getlist("isbn_id")
            submitted_quantities = request.form.getlist("quantity")

            if not submitted_isbns or len(submitted_isbns) != len(submitted_quantities):
                raise ValueError("Please select at least one book and enter its quantity.")

            # Combine repeated selections of the same book.
            quantities = {}
            for isbn_text, quantity_text in zip(submitted_isbns, submitted_quantities):
                if not isbn_text:
                    continue

                isbn_id = int(isbn_text)
                quantity = int(quantity_text)

                if quantity <= 0:
                    raise ValueError("Book quantities must be greater than zero.")

                quantities[isbn_id] = quantities.get(isbn_id, 0) + quantity

            if not quantities:
                raise ValueError("Please select at least one book.")

            with get_db_connection() as conn:
                with conn.cursor() as cur:
                    # Confirm that the customer exists.
                    cur.execute("""
                        SELECT customer_id
                        FROM bookshop.customer
                        WHERE customer_id = %s
                    """, (customer_id,))

                    if cur.fetchone() is None:
                        raise ValueError("Please select a valid customer.")

                    # Lock the selected book rows to avoid overselling stock.
                    isbn_ids = sorted(quantities.keys())
                    placeholders = ", ".join(["%s"] * len(isbn_ids))

                    cur.execute(f"""
                        SELECT isbn_id, title, price, stock
                        FROM bookshop.book
                        WHERE isbn_id IN ({placeholders})
                        ORDER BY isbn_id
                        FOR UPDATE
                    """, tuple(isbn_ids))

                    selected_books = {
                        row[0]: row for row in cur.fetchall()
                    }

                    if len(selected_books) != len(isbn_ids):
                        raise ValueError("One or more selected books do not exist.")

                    for isbn_id, quantity in quantities.items():
                        book = selected_books[isbn_id]
                        if quantity > book[3]:
                            raise ValueError(
                                f"Not enough stock for '{book[1]}'. "
                                f"Available stock: {book[3]}."
                            )

                    # Create the order.
                    cur.execute("""
                        INSERT INTO bookshop.orders (customer_id)
                        VALUES (%s)
                        RETURNING order_id
                    """, (customer_id,))

                    order_id = cur.fetchone()[0]

                    # Save order items and reduce stock.
                    for isbn_id, quantity in quantities.items():
                        book = selected_books[isbn_id]
                        unit_price = book[2]

                        cur.execute("""
                            INSERT INTO bookshop.order_books
                                (order_id, isbn_id, quantity, unit_price)
                            VALUES (%s, %s, %s, %s)
                        """, (order_id, isbn_id, quantity, unit_price))

                        cur.execute("""
                            UPDATE bookshop.book
                            SET stock = stock - %s
                            WHERE isbn_id = %s
                        """, (quantity, isbn_id))

            flash(f"Order #{order_id} created successfully!", "success")
            return redirect(url_for("orders_page"))

        except ValueError as error:
            flash(str(error), "error")
        except Exception:
            app.logger.exception("Failed to create order")
            flash(
                "Could not create the order. No order or stock changes were saved.",
                "error"
            )

    return render_template(
        "order_form.html",
        customers=customers,
        books=books
    )


@app.route("/orders/<int:order_id>")
def order_details(order_id):
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT o.order_id, c.cust_name, c.cust_phone,
                       c.cust_email, c.cust_addr, o.order_date
                FROM bookshop.orders o
                JOIN bookshop.customer c
                    ON c.customer_id = o.customer_id
                WHERE o.order_id = %s
            """, (order_id,))
            order = cur.fetchone()

            if order is None:
                flash("Order not found.", "error")
                return redirect(url_for("orders_page"))

            cur.execute("""
                SELECT b.isbn_id, b.title, ob.quantity,
                       ob.unit_price,
                       (ob.quantity * ob.unit_price) AS line_total
                FROM bookshop.order_books ob
                JOIN bookshop.book b
                    ON b.isbn_id = ob.isbn_id
                WHERE ob.order_id = %s
                ORDER BY b.title
            """, (order_id,))
            items = cur.fetchall()

    total = sum(
        (item[4] for item in items),
        Decimal("0.00")
    )

    return render_template(
        "order_details.html",
        order=order,
        items=items,
        total=total
    )


if __name__ == "__main__":
    app.run(debug=True)
