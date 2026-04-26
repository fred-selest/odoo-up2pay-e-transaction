{
    "name": "Payment Up2pay",
    "version": "19.0.1.0.0",
    "category": "Accounting/Payment Acquirers",
    "summary": "Payment provider for Up2pay E-Transactions",
    "description": """
        Payment provider for Up2pay E-Transactions
        ===========================================
        This module allows you to process payments through Up2pay E-Transactions payment gateway.
        
        Features:
        - Payment by redirection to Up2pay platform
        - HMAC-SHA512 signature authentication
        - IPN (Instant Payment Notification) support
    """,
    "author": "Your Company",
    "website": "https://www.yourcompany.com",
    "license": "LGPL-3",
    "depends": [
        "payment",
        "web",
    ],
    "data": [
        "views/payment_provider_views.xml",
        "data/payment_provider_data.xml",
    ],
    "installable": True,
    "application": False,
    "auto_install": False,
}
