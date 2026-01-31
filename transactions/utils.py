from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from django.core.files.base import ContentFile
from io import BytesIO

def generate_invoice_pdf(transaction):
    """
    Generates a simple PDF invoice for a transaction.
    Returns a ContentFile capable of being saved to a FileField.
    """
    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=letter)
    
    # Header
    p.setFont("Helvetica-Bold", 16)
    p.drawString(100, 750, "Nexus Auctions & Store")
    p.setFont("Helvetica", 12)
    p.drawString(100, 730, "Invoice")

    # Details
    p.drawString(100, 700, f"Invoice ID: {transaction.id}")
    p.drawString(100, 680, f"Date: {transaction.transaction_date.strftime('%Y-%m-%d %H:%M')}")
    p.drawString(100, 660, f"Seller: {transaction.seller.username}")
    p.drawString(100, 640, f"Buyer: {transaction.buyer.username}")
    
    # Item
    p.drawString(100, 600, "Product:")
    p.drawString(120, 580, f"{transaction.product.title}")
    
    # Total
    p.setFont("Helvetica-Bold", 14)
    p.drawString(100, 500, f"Total Amount: ${transaction.amount}")
    
    p.showPage()
    p.save()
    
    pdf = buffer.getvalue()
    buffer.close()
    
    file_name = f"invoice_{transaction.id}.pdf"
    return ContentFile(pdf, name=file_name)
