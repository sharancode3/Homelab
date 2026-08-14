from abc import ABC, abstractmethod
import logging

logger = logging.getLogger(__name__)

class EmailProvider(ABC):
    @abstractmethod
    def send_verification_email(self, to_email: str, token: str, project_id: str):
        pass
        
    @abstractmethod
    def send_password_reset_email(self, to_email: str, token: str, project_id: str):
        pass


class MockEmailProvider(EmailProvider):
    def __init__(self):
        self.sent_emails = []
        
    def send_verification_email(self, to_email: str, token: str, project_id: str):
        email_data = {
            "type": "verification",
            "to": to_email,
            "token": token,
            "project_id": project_id
        }
        self.sent_emails.append(email_data)
        logger.info(f"MOCK EMAIL: Sent verification email to {to_email} for project {project_id} (Token: ***MASKED***)")
        
    def send_password_reset_email(self, to_email: str, token: str, project_id: str):
        email_data = {
            "type": "password_reset",
            "to": to_email,
            "token": token,
            "project_id": project_id
        }
        self.sent_emails.append(email_data)
        logger.info(f"MOCK EMAIL: Sent password reset email to {to_email} for project {project_id} (Token: ***MASKED***)")
