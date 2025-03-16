# Libre Shop - Pdf

A Python-based PDF generation service for creating invoices, shipping documents, and order confirmations.

## Service Description

The PDF service runs on port 1111 and provides endpoints for generating various types of PDF documents using LaTeX templates. It uses Pandoc to convert YAML/Markdown content to PDF.

## Docker Usage

```shell
docker run -d -p 1111:1111 -v ./data:/app/data libreshop/pdf:latest
```

## Templates

The service uses LaTeX templates stored in `/app/data/templates/`:
- `invoice-scrlttr2.tex` - Invoice template
- `shipping-note-scrlttr2.tex` - Shipping note template
- `order-confirmation.tex` - Order confirmation template
- `RE.pdf` - Letterhead template

## API Endpoints

- `/v1` - Information endpoint showing version and available routes
- `/v1/invoice` - POST endpoint for generating invoice PDFs
- `/v1/shipping` - POST endpoint for generating shipping note PDFs
- `/v1/order-confirmation` - POST endpoint for generating order confirmation PDFs
- `/v1/delete/pdf` - DELETE endpoint to clean up PDF files
- `/v1/delete/all` - DELETE endpoint to clean up all files in the output directory
- `/health` - Health check endpoint for monitoring service status

## Environment Variables

No specific environment variables required for basic operation, but ensure the service has:
- Write access to /app/data/output directory
- Access to Pandoc for PDF generation

## API Usage

### Generate Invoice PDF

```shell
curl -X POST http://localhost:1111/v1/invoice \
  -H "Content-Type: application/json" \
  -d '{
    "subject": "Invoice #1234",
    "date": "2025-03-16",
    "me": {
      "companyname": "Mueller Prints",
      "name": "John Mueller",
      "street": "123 Print St.",
      "city": "Berlin, 10115",
      "email": "contact@muellerprints.com",
      "url": "www.muellerprints.com"
    },
    "to": {
      "name": "Customer Name",
      "address": ["Customer Address", "City, Postal Code"]
    },
    "invoice_nr": "INV-1234",
    "author": "John Mueller",
    "city": "Berlin",
    "VAT": 19,
    "service": [
      {
        "description": "Premium Print Service",
        "price": 99.99,
        "details": ["High-quality paper", "Full color printing"]
      }
    ],
    "closingnote": "Thank you for your business!",
    "body": "Additional detailed information about the order."
  }'
```

### Generate Shipping Note

```shell
curl -X POST http://localhost:1111/v1/shipping \
  -H "Content-Type: application/json" \
  -d '{
    "subject": "Shipping Note",
    "date": "2025-03-16",
    "me": {
      "companyname": "Mueller Prints",
      "name": "John Mueller",
      "street": "123 Print St.",
      "city": "Berlin, 10115",
      "email": "contact@muellerprints.com",
      "url": "www.muellerprints.com"
    },
    "to": {
      "name": "Customer Name",
      "address": ["Customer Address", "City, Postal Code"]
    },
    "invoice_nr": "SHP-1234",
    "author": "John Mueller",
    "city": "Berlin",
    "VAT": 19,
    "service": [
      {
        "description": "Shipping Materials",
        "price": 5.99,
        "details": ["Protective packaging"]
      }
    ],
    "closingnote": "Thank you for your order!",
    "body": "Your order has been shipped and will arrive within 3-5 business days."
  }'
```

### Generate Order Confirmation

```shell
curl -X POST http://localhost:1111/v1/order-confirmation \
  -H "Content-Type: application/json" \
  -d '{
    "subject": "Order Confirmation",
    "date": "2025-03-16",
    "me": {
      "companyname": "Mueller Prints",
      "name": "John Mueller",
      "street": "123 Print St.",
      "city": "Berlin, 10115",
      "email": "contact@muellerprints.com",
      "url": "www.muellerprints.com"
    },
    "to": {
      "name": "Customer Name",
      "address": ["Customer Address", "City, Postal Code"]
    },
    "invoice_nr": "ORD-1234",
    "author": "John Mueller",
    "city": "Berlin",
    "VAT": 19,
    "service": [
      {
        "description": "Product Order",
        "price": 79.99,
        "details": ["Item #1234", "Quantity: 2"]
      }
    ],
    "closingnote": "We appreciate your business!",
    "body": "Your order has been received and is being processed."
  }'
```

### Delete Generated PDFs

```shell
curl -X DELETE http://localhost:1111/v1/delete/pdf
```

### Delete All Files in Output Directory

```shell
curl -X DELETE http://localhost:1111/v1/delete/all
```

### Check Service Health

```shell
curl http://localhost:1111/health
```

## Prometheus Metrics

The service exposes Prometheus metrics:
- `pdf_generation_total` - Counter for PDFs generated, with labels for different document types

## Development

Open virtual environment for installing python packages
```shell
. .venv/bin/activate
```

Install packages
```shell
pip install -r requirements.txt
```

Or install individual packages
```shell
pip install prometheus_client
```

Move installed packages to `requirements.txt`
```shell
pip freeze > requirements.txt
```
