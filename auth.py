import random
import smtplib
from flask_mail import Mail, Message
import app

def generate_unique_code():
    """
    Docstring
    """
    code = ''
    for i in range(6):
        num = random.randint(0, 9)
        code += str(num)
    
    return code

def send_email(recipient, subject, message_body):
    """
    Docstring
    """
    msg = Message (
        subject,
        recipients = [recipient],
        body = message_body
    )

    try:
        app.mail.send(msg)
        return 'Sent', 200
    except ConnectionError as e:
        return f"Connection error: {str(e)}", 500
    except smtplib.SMTPException as e:
        return f"SMTP error: {str(e)}", 500