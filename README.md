#BOOKIT API

Bookit API is a FastAPI-based backend service for bookings that is built using POSTGRESQL, Docker. ookings, built with PostgreSQL and Docker. 
It supports JWT authentication, database migrations via Alembic, and can be served behind Nginx.

Features of Bookit
FastAPI backend
PostgreSQL database
Dockerized setup
Alembic migrations for database versioning
JWT authentication (access/refresh tokens)
User Management (admin/user roles)
Service Management (CRUD operations)  
Booking System with conflict detection
Review System
Swagger UI documentation (`/docs`)
Environment variable configuration

To start you need to clone the repo to your IDE : https://github.com/ObongIkoh/Book_It.git
set up your virtual environment: python3 -m venv venv or env
to activate it; bash: source venv/Scripts/activate, powershell: .\.venv\Scripts\Activate or depending on the IDE you are using
then you install the requirements: pip install -r requirements.txt
when you are done with that, you'll set up your docker and thenrun alembic migrations
using bash: bash
docker-compose build --no-cache
docker-compose up -d
This will start up three containers; bookit-db (PostgreSQL database), bookit-api (FastAPI application), bookit-nginx (Optional Nginx reverse proxy)
alembic migration ==> bash: alembic upgrade head

You can either load it through uvicorn: uvicorn app.main:app --reload or go directly to the API: Swagger UI: http://localhost:8000/docs

Architecture of Bookit API
FastAPI: High-performance web framework
SQLAlchemy: ORM with PostgreSQL
Alembic: Database migrations
JWT: Token-based authentication
Pydantic: Data validation
Repository Pattern: Clean data access layer
Service Layer: Business logic separation


Endpoints

Authentication
POST /auth/register - Register new user
POST /auth/login - Login user
POST /auth/refresh - Refresh access token
POST /auth/logout - Logout (revoke refresh token)
GET /auth/me - Read Current User

Users
GET /me/ - Get current user profile
PATCH /me/ - Update current user profile
GET /users/me/profile - Get my profile
GET /users/me/statistics - get my statistics
POST /users/me/change-password - change password
DELETE /users/me - delete my account


Services (Public read, Admin manage)
GET /services/ - List services (with filters)
GET /services/{id} - Get service details
POST /services/ - Create service (Admin only)
PATCH /services/{id} - Update service (Admin only)
DELETE /services/{id} - Delete service (Admin only)

Bookings
POST /bookings/ - Create booking
GET /bookings/ - List bookings (own bookings for users, all for admins)
GET /bookings/{id} - Get booking details
PATCH /bookings/{id} - Update booking (reschedule/cancel)
DELETE /bookings/{id} - Delete booking

Reviews
POST /reviews/ - Create review (for completed bookings)
GET /reviews/service/{service_id} - List reviews for service
PATCH /reviews/{id} - Update review
DELETE /reviews/{id} - Delete review

Each of these endpoints have comprehensive error handling with appropraite HTTP status codes
Error Handling Strategy
Custom Exception Hierarchy:
a. BookItException (base)
b. ValidationError (400)
c. AuthenticationError (401)
d. AuthorizationError (403)
e. NotFoundError (404)
f. ConflictError (409)
g. DatabaseError (500)

Global Exception Handlers:
a. Catches exceptions at application level
b. Returns consistent JSON error responses
c. Logs errors for debugging
d. Never exposes internal details to users

Features of each endpoint
Authentication & Authorization
a. JWT-based authentication (access + refresh tokens)
b. Role-based access control (user/admin)
c. Secure password hashing with bcrypt
d. Token revocation support


Service Management
a. CRUD operations for services
b. Service filtering and search
c. Active/inactive status management
d. Admin-only management

Booking System
a. Create, update, and cancel bookings
b. Automatic booking conflict detection
c. Status workflow (pending → confirmed → completed → cancelled)
d. Prevents double-booking with time slot validation
Review System
a. Review completed bookings
b. Rating system (1-5 stars)
c. Review statistics and aggregations
d. One review per booking constraint

To carry out testing
a. Run all tests
bash: pytest -v
b. Run specific tests
bash: pytest tests/test_booking_conflict.py -v

For docker
bash: docker-compose up --build
when done with building you run this; bash: docker-compose up -d db

Database Design Choice
I chose PostgreSQL over MongoDB because:
a. ACID compliance - Critical for preventing double bookings
b. Strong relationships - Foreign keys ensure data integrity
c. Complex queries - Efficient JOINs for filtering bookings
d. Transactional consistency - Important for financial data (bookings)
e. Mature tooling - Better support for migrations and async operations
Key Design:
a. UUID primary keys for security and distributed systems
b. Proper foreign key relationships with CASCADE deletes
c. Indexes on frequently queried fields (email, start_time)
d. Enum types for status fields (type safety)

Security Measures
a. Password Security: bcrypt hashing with salt
b. JWT Tokens: Short-lived access tokens (60 min), longer refresh tokens (7 days)
c. Token Revocation: Refresh tokens stored in database for logout
d. CORS: wildcard
e. SQL Injection: SQLAlchemy ORM prevents injection
f. Input Validation: Pydantic schemas validate all inputs

Quick API Examples
Register User:
bash: curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "name": "John Doe",
    "email": "john@example.com",
    "password": "password123"
  }'
Login:
bash: curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "john@example.com",
    "password": "password123"
  }'
Get Profile (Protected):
bash: curl -X GET http://localhost:8000/users/me \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
Create Service (Admin Only):
bash: curl -X POST http://localhost:8000/services/ \
  -H "Authorization: Bearer ADMIN_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Massage Therapy",
    "description": "60-minute relaxing massage",
    "price": 89.99,
    "duration_minutes": 60,
    "is_active": true
  }'
Create Booking:
bash: curl -X POST http://localhost:8000/bookings/ \
  -H "Authorization: Bearer USER_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "service_id": "550e8400-e29b-41d4-a716-446655440000",
    "start_time": "2024-12-15T10:00:00"
  }'








