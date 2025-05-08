# 🛍️ Product Recommendation API

This is a FastAPI-based backend that provides an API for browsing products and getting recommendations based on user behavior and product co-occurrence. Built with asynchronous I/O, modular services, and test coverage, this project, I believe, demonstrates scalable backend design.

---

## 📁 Project Structure

```
.
├── app/
│   ├── db.py                 # MongoDB connection
│   ├── main.py               # FastAPI application
│   ├── models.py             # Data models (if any)
│   ├── stats.py              # Product statistics logic
│   ├── templates/            # HTML templates (e.g. index.html)
│   ├── utils/                # Utility functions
│   │   ├── db_utils.py
│   │   └── utils.py
│   └── services/             # Recommender logic and background updates
│       ├── recommender.py
│       └── updater.py
├── tests/                    # Unit tests
│   ├── conftest.py
│   ├── test_index.py
│   ├── test_products.py
│   ├── test_recommendation.py
├── README.md
├── requirements.txt
```

---

## 🚀 Features

- ✅ RESTful API with FastAPI
- 🧠 Dual recommendation engines:
  - User-based collaborative filtering
  - Co-occurrence-based recommendation
- 🔁 Background tasks to refresh stats and recommenders
- 🔍 Rich product search with multiple query filters
- 📊 Product stats integration
- 🧪 Unit tests with Pytest

---

## ⚙️ Setup Instructions

### 1. Clone the repository

```bash
git clone https://github.com/JakubCiesko/bloom-product-api.git
cd bloom-product-api
```

### 2. Create and activate a virtual environment

```bash
python -m venv venv
source venv/Scripts/activate  # Git Bash / Windows
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Run MongoDB using Docker

```bash
docker run -d -p 27017:27017 --name mongo mongo
```

### 5. Load data into MongoDB

```bash
python app/utils/db_utils.py path_to_products_json.json --products path_to_events_json.json --events
```
Might add --keep_db_content flag to not empty the database first.

### 6. Run the API

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

---

## 📡 API Endpoints

### `GET /`
Returns a basic HTML page showing server time (`index.html`).

### `GET /products`
Returns filtered products.
**Query params**:
- `id`, `title`, `category`, `min_price`, `max_price`, `color`, `material`, `sizes`, `brand`

### `GET /recommend`
Returns recommended products.
**Query params**:
- `product_id` – ID of a reference product
- `user_id` – If provided, uses user-personalized recommender
- `recommend_n` – Number of products to recommend (default: 5)
- `sample=true` – Return a sampled subset

---

## ✅ Testing

Run unit tests using:

```bash
python -m pytest tests/
```

Test coverage includes:
- Index route
- Product search logic
- Recommendation logic (user & non-user-based)

---

## 💡 Ideas to Improve

- Improve recommender fallback logic
...
---

## 🧑 Author
Jakub Čieško

## Additional Info

Built as part of a technical assessment for a backend internship position.  
Feedback welcome!

---

