# Aura AI 2.0

## Overview

This is a Flask-based web application for an AI assistant dashboard called "Aura". The application provides a comprehensive interface for managing various AI features including face recognition, emotion detection, voice controls, and memory management. It uses Flask as the backend framework with SQLAlchemy for database operations and includes a modern responsive frontend built with Bootstrap.

## System Architecture

### Backend Architecture
- **Framework**: Flask 3.1.1 with Gunicorn WSGI server
- **Database**: PostgreSQL with Flask-SQLAlchemy ORM
- **Authentication**: Flask-Login for session management
- **Validation**: Email-validator for input validation
- **Deployment**: Configured for autoscaling deployment on Replit

### Frontend Architecture
- **UI Framework**: Bootstrap 5.3.0 for responsive design
- **Icons**: Font Awesome 6.4.0 for iconography
- **Charts**: Chart.js for data visualization
- **JavaScript**: Vanilla ES6+ with modular API wrapper
- **Styling**: Custom CSS with CSS variables for theming

## Key Components

### Core Application Files
- `main.py`: Main Flask application entry point (implied from deployment config)
- `templates/index.html`: Primary dashboard template with navigation and content sections
- `static/js/app.js`: Main dashboard application logic and UI interactions
- `static/js/api.js`: API wrapper class for backend communication
- `static/css/style.css`: Custom styling with CSS variables and responsive design

### Database Layer
- PostgreSQL database configured via Flask-SQLAlchemy
- Session management through Flask-Login
- User authentication and authorization system

### API Structure
The application includes endpoints for:
- Face recognition (`/face_add`)
- Audio processing (blob responses)
- Image processing (blob responses)
- General data operations (JSON responses)

## Data Flow

1. **User Authentication**: PIN-based unlock system with modal interface
2. **Dashboard Navigation**: Single-page application with section-based routing
3. **Real-time Updates**: Auto-refresh intervals for live data
4. **Media Processing**: File upload handling for face recognition and other AI features
5. **API Communication**: RESTful API calls with proper error handling and content-type detection

## External Dependencies

### Python Dependencies
- Flask ecosystem (Flask, Flask-SQLAlchemy, Flask-Login)
- PostgreSQL driver (psycopg2-binary)
- Email validation utilities
- Gunicorn production server

### Frontend Dependencies (CDN)
- Bootstrap 5.3.0 for UI components
- Font Awesome 6.4.0 for icons
- Chart.js for data visualization

### System Dependencies
- PostgreSQL database server
- OpenSSL for secure connections

## Deployment Strategy

- **Platform**: Replit with autoscale deployment target
- **Server**: Gunicorn WSGI server binding to 0.0.0.0:5000
- **Development**: Hot reload enabled for development workflow
- **Environment**: Python 3.11 with Nix package management
- **Scaling**: Configured for automatic scaling based on demand

The application uses Replit's workflow system for streamlined development and deployment, with proper port configuration and parallel task execution.

## Changelog

```
Changelog:
- June 22, 2025. Initial setup
```

## User Preferences

```
Preferred communication style: Simple, everyday language.
```
