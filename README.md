 BooksVault - Bookshop Management System

BooksVault is a web-based **Bookshop Management System** designed to simplify and organize bookshop operations. It allows users to manage book inventory, customers, dealers, and sales orders through a clean and user-friendly interface.

The application uses Python Flask for backend processing and PostgreSQL for storing and managing data.

 Features

- **Dashboard:** View bookshop summaries, including book inventory, customers, orders, and low-stock information.
- **Book Management:** Add, view, edit, delete, and search books.
- **Customer Management:** Maintain customer details and manage customer records.
- **Dealer Management:** Store and manage book dealer or supplier information.
- **Order Management:** Create customer orders with multiple books and quantities.
- **Automatic Stock Updates:** Update available book stock when an order is successfully placed.
- **Order Tracking:** View saved orders and their calculated totals.
- **Search Functionality:** Find books and records more easily.
- **Database Integrity:** Use primary keys, foreign keys, and constraints to maintain consistent data.
- **User-Friendly Interface:** A clean interface with a sage-green and ivory color theme.

Technologies Used

| Technology | Purpose |
|---|---|
| Python | Backend programming |
| Flask | Web application framework |
| PostgreSQL | Relational database |
| Psycopg | Python–PostgreSQL connectivity |
| HTML5 | Webpage structure |
| CSS3 | Styling and layout |
| Jinja | Dynamic HTML templates |
| pgAdmin 4 | Database administration |
| Git and GitHub | Version control and source code hosting |

Project Structure

```text
BooksVault/
├── app.py
├── requirements.txt
├── .env.example
├── .gitignore
├── db/
│   ├── schema.sql
│   └── sample_data.sql
├── static/
│   ├── style.css
│   └── bookshop.png
└── templates/
    ├── base.html
    ├── index.html
    ├── books.html
    ├── book_form.html
    ├── customers.html
    ├── customer_form.html
    ├── dealers.html
    ├── dealer_form.html
    ├── orders.html
    └── order_form.html
```

*Note: The exact files in `static/` and `templates/` may vary as the project develops.*

Prerequisites

Before running BooksVault, install:

- Python 3
- PostgreSQL
- pgAdmin 4 (recommended for database management)
- Git (optional, for cloning the repository)

Installation and Setup

 1. Clone the repository

```bash
git clone https://github.com/dot-rashy/BooksVault.git
cd BooksVault
```

 2. Create a Python virtual environment

```bash
python -m venv venv
```

Activate it on Windows PowerShell:

```powershell
.\venv\Scripts\Activate.ps1
```

 3. Install dependencies

```bash
pip install -r requirements.txt
```

 4. Create the PostgreSQL database

Open pgAdmin 4 and create a database named:

```text
bookshop_db
```

Open the Query Tool for `bookshop_db` and execute the SQL statements in:

```text
db/schema.sql
```

This creates the `bookshop` schema and its tables.

Optional: Execute `db/sample_data.sql` if you want to insert the demonstration records supplied with the project. Run it only when appropriate for your database.

### 5. Configure environment variables

Create a local file named `.env` in the project root, alongside `app.py`.

Add your own PostgreSQL connection details:

```dotenv
DB_HOST=localhost
DB_PORT=5432
DB_NAME=bookshop_db
DB_USER=postgres
DB_PASSWORD=your_local_postgres_password
FLASK_SECRET_KEY=replace_with_a_random_secret
```

Replace the example password and secret with your own values.

**Security note:** Never upload your actual `.env` file or expose database passwords and secret keys in a public repository. The `.env.example` file is provided as a configuration template.

### 6. Run the application

With the virtual environment activated, run:

```bash
python app.py
```

Open the local address displayed by Flask in your terminal. If the application uses the default Flask development settings, it is commonly:

```text
http://127.0.0.1:5000
```

## 🗄️ Database Design

BooksVault uses PostgreSQL with a schema named `bookshop`.

| Table | Description |
|---|---|
| `book` | Stores book details, prices, authors, publishers, and stock |
| `customer` | Stores customer information |
| `dealer` | Stores dealer and supplier information |
| `book_supplier` | Connects books with their suppliers |
| `orders` | Stores customer order information |
| `order_books` | Stores the books, quantities, and unit prices in each order |

### Database Relationships

- A customer can place multiple orders.
- An order can contain multiple books.
- A book can appear in multiple orders.
- A dealer can supply multiple books.
- A book can be associated with multiple dealers.

Primary keys and foreign keys help maintain valid relationships between the tables. Constraints help prevent invalid prices, negative stock, and invalid quantities.

 Order Processing

When an order is created:

1. The user selects a customer.
2. The user chooses one or more books and specifies quantities.
3. The application validates the submitted information.
4. The backend checks that sufficient stock is available.
5. The order and its items are saved in PostgreSQL.
6. The available stock is reduced after a successful order.

The estimated order total is calculated from the selected books, quantities, and unit prices.

 Security and Configuration

- Database credentials are stored in a local `.env` file.
- `.gitignore` excludes sensitive configuration and generated files from normal Git tracking.
- `.env.example` documents the required configuration variables without containing real credentials.
- Parameterized SQL queries help protect against SQL injection.
- Backend validation checks submitted values before database operations.

For production use, configure a strong secret key, use appropriate database permissions, and deploy behind a production-ready web server.

 Project Objectives

- Simplify bookshop inventory management.
- Maintain organized customer and dealer records.
- Record customer purchases and order totals.
- Keep stock levels updated after sales.
- Reduce manual record-keeping and improve data consistency.
- Demonstrate the integration of a Python web framework with a relational database.

 Future Enhancements

Potential improvements include:

- User authentication and role-based access.
- Sales reports and analytics.
- Low-stock alerts.
- Invoice generation and printing.
- Supplier purchase and stock-restocking workflows.
- Data export and automated database backups.





