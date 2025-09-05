# Salão Agendamento - Sistema de Agendamento para Salões de Beleza

## Overview

This is a Django-based appointment scheduling system designed for beauty salons and hair salons. The application provides a multi-user platform where administrators can manage merchants (salon owners), merchants can manage their employees and services, and customers can book appointments through a public interface. The system supports role-based access control with three user types: administrators, merchants (salon owners), and employees.

## User Preferences

Preferred communication style: Simple, everyday language.

## System Architecture

### Backend Framework
The application is built on Django 5.2.6, following the Model-View-Template (MVT) pattern. The system uses Django's built-in authentication system with a custom User model that extends AbstractUser to support different user types and additional profile information.

### Database Design
The system uses Django's ORM with the following core models:
- **Custom User Model**: Extends AbstractUser with additional fields for user types (admin, comerciante, funcionario), phone, birth date, profile photo, and status tracking
- **Comerciante (Merchant)**: Represents salon owners with business information including salon name, CNPJ, address, business hours, and logo
- **Funcionario (Employee)**: Links employees to merchants with specializations and schedule management
- **Servico (Service)**: Defines services offered by salons with pricing and duration
- **Cliente (Client)**: Customer information for appointment booking
- **Agendamento (Appointment)**: Core appointment entity linking clients, employees, services, and time slots

### User Authentication & Authorization
The system implements role-based access control through:
- Custom middleware (UserTypeMiddleware) that controls access based on user type
- Three distinct user roles with different permission levels
- Session-based authentication with automatic redirection based on user role
- Public access for appointment booking without authentication

### Application Structure
The project is organized into modular Django apps:
- **accounts**: User management, authentication, and profile handling
- **admin_panel**: Administrative interface for system-wide management
- **comerciante_panel**: Merchant dashboard for business management
- **agendamento**: Public appointment booking system and appointment management
- **salao_agendamento**: Main project configuration

### Frontend Architecture
The frontend uses a template-based approach with:
- Bootstrap 5.3.0 for responsive design and UI components
- Font Awesome 6.4.0 for icons
- Custom CSS with CSS variables for consistent theming
- JavaScript for dynamic interactions (AJAX for appointment booking)
- Template inheritance structure with base templates for each user role

### API Design
The system includes JSON-based APIs for:
- Fetching available employees for specific services
- Getting available time slots for employees
- Creating appointments dynamically
- Verifying appointment availability

### File Upload Handling
The system handles file uploads for:
- User profile photos (upload_to='perfil/')
- Salon logos (upload_to='logos/')
- Uses Pillow for image processing

## External Dependencies

### Core Dependencies
- **Django 5.2.6**: Main web framework
- **djangorestframework**: For API functionality
- **django-cors-headers**: Cross-origin resource sharing support
- **Pillow**: Image processing for file uploads

### Frontend Dependencies (CDN)
- **Bootstrap 5.3.0**: CSS framework for responsive design
- **Font Awesome 6.4.0**: Icon library
- **QR Code generation**: For generating appointment booking QR codes

### Development Tools
- **Django Management Commands**: Custom command for creating admin users
- **Django Migrations**: Database schema management
- **Django Static Files**: Static asset handling

### Deployment Considerations
- Configured for Replit deployment with CSRF trusted origins
- Static and media file serving configuration
- Environment variable support for settings
- Debug mode enabled for development