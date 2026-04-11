# Project Dependencies

This document lists all external dependencies and libraries used across the ApiCortex microservices project.

## Frontend

**Technology Stack:** Next.js 16, React 19, TypeScript, Tailwind CSS, Shadcn UI

**Runtime Dependencies:**

| Package | Version | Usage |
|---------|---------|-------|
| @base-ui/react | ^1.2.0 | Unstyled, accessible UI primitives for building custom components |
| @hookform/resolvers | ^5.2.2 | Form validation schema integration with React Hook Form |
| @tanstack/react-query | ^5.90.21 | Data fetching, caching, and state management for API calls |
| axios | ^1.15.0 | HTTP client for making API requests to backend services |
| class-variance-authority | ^0.7.1 | Utility for creating component variants with different styles |
| clsx | ^2.1.1 | Utility for conditionally joining CSS class names |
| framer-motion | ^12.35.2 | Animation library for smooth UI transitions and gestures |
| lucide-react | ^0.577.0 | Icon library providing SVG icons for UI elements |
| next | 16.2.3 | React framework for building the application with SSR/RSC |
| next-themes | ^0.4.6 | Theme management for dark/light mode switching |
| react | 19.2.3 | Core UI library for building component-based interfaces |
| react-dom | 19.2.3 | React package for DOM rendering |
| react-hook-form | ^7.71.2 | Form state management and validation |
| react-resizable-panels | ^4.7.2 | Resizable panel layouts for dashboards and split views |
| recharts | ^3.8.0 | Charting library for data visualization components |
| shadcn | ^4.0.2 | Component library with accessible, customizable UI components |
| sonner | ^2.0.7 | Toast notification system for user feedback |
| tailwind-merge | ^3.5.0 | Utility for merging Tailwind CSS class names without conflicts |
| tw-animate-css | ^1.4.0 | Additional Tailwind CSS animation utilities |
| zod | ^4.3.6 | Schema validation for forms and API data validation |

**Dev Dependencies:**

| Package | Version | Usage |
|---------|---------|-------|
| @tailwindcss/postcss | ^4 | PostCSS plugin for Tailwind CSS integration |
| @types/node | ^20 | TypeScript type definitions for Node.js APIs |
| @types/react | ^19 | TypeScript type definitions for React |
| @types/react-dom | ^19 | TypeScript type definitions for React DOM |
| eslint | ^9 | JavaScript/TypeScript linter for code quality |
| eslint-config-next | 16.1.6 | ESLint configuration preset for Next.js projects |
| tailwindcss | ^4 | Utility-first CSS framework for styling |
| typescript | ^5 | Type checker and compiler for TypeScript language |

**Package Manager:** npm@11.11.1

---

## dbmanage

**Technology Stack:** Bun, Drizzle ORM, PostgreSQL, TypeScript

**Runtime Dependencies:**

| Package | Version | Usage |
|---------|---------|-------|
| dotenv | ^16.4.7 | Load environment variables from .env files |
| drizzle-orm | ^0.45.2 | Type-safe ORM for database schema management and queries |
| pg | ^8.14.1 | PostgreSQL client for database connectivity |

**Dev Dependencies:**

| Package | Version | Usage |
|---------|---------|-------|
| drizzle-kit | ^0.31.4 | CLI tool for Drizzle ORM migrations and studio |
| typescript | ^5.8.2 | Type checker and compiler for TypeScript language |

**Package Manager:** bun@1.3.4

---

## control-plane

**Technology Stack:** Python, FastAPI, PostgreSQL, Kafka, Auth0/OAuth

**Runtime Dependencies:**

| Package | Version | Usage |
|---------|---------|-------|
| fastapi | 0.115.7 | Web framework for building RESTful API endpoints |
| uvicorn[standard] | 0.32.1 | ASGI server for running FastAPI application |
| sqlalchemy | 2.0.37 | SQL toolkit and ORM for database operations |
| psycopg2-binary | 2.9.10 | PostgreSQL adapter for Python database connectivity |
| pydantic | 2.10.5 | Data validation and settings management using type hints |
| pydantic-settings | 2.7.1 | Configuration management with environment variables |
| python-jose[cryptography] | 3.3.0 | JWT token creation and verification for authentication |
| authlib | 1.6.9 | OAuth and OpenID Connect authentication framework |
| httpx | 0.28.1 | Async HTTP client for making external API calls |
| bcrypt | 4.2.1 | Password hashing for secure credential storage |
| confluent-kafka | >=2.4.0 | Apache Kafka client for event streaming |
| python-multipart | 0.0.22 | Multipart form data parsing for file uploads |
| python-json-logger | 3.2.1 | Structured JSON logging for better observability |
| email-validator | 2.2.0 | Email address validation for user registration |
| itsdangerous | 2.2.0 | Secure serialization for tokens and signed data |

**Python Version:** 3.11.9

---

## ml-service

**Technology Stack:** Python, XGBoost, SHAP, Kafka, PostgreSQL

**Runtime Dependencies:**

| Package | Version | Usage |
|---------|---------|-------|
| confluent-kafka | >=2.4.0 | Apache Kafka client for consuming telemetry events |
| numpy | >=1.26.0 | Numerical computing for data preprocessing and feature engineering |
| pandas | >=2.2.0 | Data manipulation and analysis for model inputs |
| psycopg2-binary | >=2.9.9 | PostgreSQL adapter for fetching historical data |
| pydantic | >=2.7.0 | Data validation for model inputs and outputs |
| python-dotenv | >=1.0.1 | Environment variable loading from .env files |
| joblib | >=1.4.0 | Model persistence for saving/loading trained models |
| python-snappy | >=0.7.3 | Snappy compression for efficient data storage |
| shap | >=0.45.0 | Explainable AI for model predictions interpretability |
| uvloop | >=0.19.0 (sys_platform != "win32") | High-performance asyncio event loop |
| xgboost | >=2.0.0 | Gradient boosting framework for failure prediction model |

**Python Version:** 3.11.9

---

## ingest-service

**Technology Stack:** Go 1.26, PostgreSQL, Kafka, ZeroLog

**Runtime Dependencies:**

| Module | Version | Usage |
|--------|---------|-------|
| github.com/google/uuid | v1.6.0 | UUID generation for unique event identifiers |
| github.com/joho/godotenv | v1.5.1 | Environment variable loading from .env files |
| github.com/lib/pq | v1.10.9 | PostgreSQL driver for database connectivity |
| github.com/rs/zerolog | v1.33.0 | High-performance JSON logging for observability |
| github.com/segmentio/kafka-go | v0.4.47 | Apache Kafka client for producing telemetry events |
| golang.org/x/crypto | v0.49.0 | Cryptographic functions for security operations |
| golang.org/x/time | v0.14.0 | Extended time functionality and timezone data |

**Indirect Dependencies:**

| Module | Version | Usage |
|--------|---------|-------|
| github.com/klauspost/compress | v1.15.9 | Compression algorithms for efficient data processing |
| github.com/mattn/go-colorable | v0.1.13 | Colored terminal output for Windows compatibility |
| github.com/mattn/go-isatty | v0.0.19 | Terminal detection for proper logging format |
| github.com/pierrec/lz4/v4 | v4.1.15 | LZ4 compression for high-speed data compression |
| golang.org/x/sys | v0.42.0 | Low-level operating system primitives and syscalls |

**Go Version:** 1.26.0

---

## api-testing

**Technology Stack:** Rust, Axum, Tokio, WebSockets

**Runtime Dependencies:**

| Crate | Version | Features | Usage |
|-------|---------|----------|-------|
| axum | 0.7 | json, macros | Web framework for building REST APIs with WebSocket support |
| tokio | 1 | full | Async runtime for concurrent I/O operations |
| tower-http | 0.5 | trace, cors | HTTP middleware for tracing and CORS handling |
| serde | 1 | derive | Serialization/deserialization framework |
| serde_json | 1 | - | JSON serialization/deserialization support |
| reqwest | 0.12 | rustls-tls, json, gzip, deflate, stream | HTTP client for making API requests |
| tokio-tungstenite | 0.23 | native-tls | WebSocket client/server implementation |
| futures-util | 0.3 | - | Combinators and utilities for futures |
| tracing | 0.1 | - | Structured logging and diagnostics framework |
| tracing-subscriber | 0.3 | env-filter, json | Subscriber implementation for tracing with JSON output |
| thiserror | 1 | - | Ergonomically define custom error types |
| anyhow | 1 | - | Flexible error handling for application errors |
| http | 1 | - | HTTP types and constants for working with HTTP |
| tokio-native-tls | 0.3 | - | Native TLS support for tokio |
| native-tls | 0.2 | - | Platform-specific TLS implementation |
| url | 2 | - | URL parsing and manipulation library |

**Dev Dependencies:**

| Crate | Version | Features | Usage |
|-------|---------|----------|-------|
| axum-test | 15 | - | Testing utilities for axum applications |
| tokio-tungstenite | 0.23 | native-tls | WebSocket testing support |
| futures-util | 0.3 | - | Future combinators for async test scenarios |
| wiremock | 0.6 | - | HTTP mocking for integration testing |
| tokio | 1 | full | Async runtime for test execution |

**Rust:** 1.94

---

## DataGen

**Technology Stack:** Python, NumPy, Pandas, SciPy

**Description:** Data generation and validation scripts for synthetic microservice observability data.

**Runtime Dependencies:**

| Package | Version | Usage |
|---------|---------|-------|
| numpy | >=1.26.0 | Numerical operations for data generation and manipulation |
| pandas | >=2.2.0 | Data structures and analysis for synthetic dataset creation |
| scipy | >=1.10.0 | Scientific computing for statistical distributions |

**Python Version:** 3.11.9

---

## model

**Technology Stack:** Python, Scikit-learn, XGBoost, SHAP, Jupyter Notebooks

**Description:** Model training and evaluation notebooks for failure prediction.

**Runtime Dependencies:**

| Package | Version | Usage |
|---------|---------|-------|
| pandas | >=2.2.0 | Data manipulation and preprocessing for model training |
| numpy | >=1.26.0 | Numerical operations for feature engineering |
| matplotlib | >=3.7.0 | Plotting library for data visualization and analysis |
| seaborn | >=0.13.0 | Statistical data visualization for EDA and results |
| scikit-learn | >=1.3.0 | Machine learning algorithms and evaluation metrics |
| xgboost | >=2.0.0 | Gradient boosting for failure prediction model |
| shap | >=0.45.0 | Model explainability and feature importance analysis |
| joblib | >=1.4.0 | Model persistence for saving/loading trained models |

**Python Version:** 3.11.9

---

## Summary

| Service | Language | Primary Frameworks | Package Manager |
|---------|----------|-------------------|-----------------|
| frontend | TypeScript/JavaScript | Next.js 16, React 19 | npm |
| dbmanage | TypeScript | Drizzle ORM, Bun | bun |
| control-plane | Python | FastAPI | pip |
| ml-service | Python | XGBoost, SHAP | pip |
| ingest-service | Go | net/http, Kafka | go modules |
| api-testing | Rust | Axum, Tokio | cargo |
| DataGen | Python | NumPy, Pandas, SciPy | pip |
| model | Python | Scikit-learn, XGBoost, SHAP | pip |

**Total Unique Dependencies:** 70+ libraries across 8 services and 7 programming languages/frameworks
