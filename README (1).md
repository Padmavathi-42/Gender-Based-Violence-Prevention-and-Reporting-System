# Gender-Based Violence Prevention and Reporting System

A secure full-stack web application designed to enable anonymous reporting of gender-based violence incidents. The system leverages AI-driven sentiment analysis, predictive analytics, and WebSocket-based real-time notifications to help identify distress patterns and support proactive intervention, while prioritizing ethical AI usage and data privacy.

---

## 🔍 Problem Statement
Many victims of gender-based violence hesitate to report incidents due to fear, stigma, or lack of accessible support systems. This project aims to provide a safe, anonymous, and technology-driven platform that encourages reporting, enables early identification of high-risk situations, and supports timely responses.

---

## 🚀 Key Features
- Anonymous incident reporting through a user-friendly web interface  
- AI-based sentiment analysis to detect distress levels in user submissions  
- Predictive analytics to identify high-risk patterns  
- **Real-time alerts and notifications using WebSockets**  
- Admin dashboard for monitoring reports and analytics  
- Secure backend APIs designed to handle sensitive data responsibly  

---

## 🛠️ Tech Stack

### Frontend
- HTML  
- CSS  
- JavaScript  

### Backend
- Python  
- FastAPI  
- RESTful APIs  
- **WebSockets for real-time communication**

### AI & Analytics
- NLP-based sentiment analysis  
- Distress detection and predictive analytics  
---

## Project Structure
Gender-Based-Violence-Prevention-and-Reporting-System/
├── frontend/
│ ├── html/ # UI pages
│ ├── css/ # Stylesheets
│ ├── js/ # Client-side scripts
│ └── assets/ # Media files
│
├── backend/
│ ├── app.py # FastAPI application
│ └── distress.py # Distress detection logic
│
├── .gitignore
└── README.md

---

## Security Considerations
- Designed to handle sensitive user data responsibly  
- Supports anonymous reporting to protect user identity  
- Backend API architecture allows extension to JWT-based authentication  
- Ethical AI practices followed to minimize bias and misuse  

---

## How to Run Locally

### Backend
```bash
cd backend
pip install -r requirements.txt
uvicorn app:app --reload

Frontend
Open any HTML file from the frontend/html/ directory in a browser.
