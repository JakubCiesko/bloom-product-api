# 🛍️ Product API

This is a FastAPI-based backend that provides an API for browsing products and getting recommendations based on user behavior and product co-occurrence. Built with asynchronous I/O, modular services, and test coverage, this project, I believe, demonstrates scalable backend design.

    🧪 Built as part of a technical assessment for an internship. Feedback welcome!

---

## DOCKER 

## 🐳 Running with Docker

This project supports Docker for simplified setup.

### Step 1: Build the containers

```bash
docker-compose build
```
### Step 2: Start the services
```bash
docker-compose up
```

### Step 3: Populate the db
Once MongoDB is running, populate the database (for example) with the default data already present in the container:

```bash
docker exec -it bloomreach-app-1 python -m app.utils.db_utils --products data/catalog.json --events data/events.json
```
Adjust the names of the containers if they are different for you.

### Step 4: Force the app to reload updated data
Call the /force_update endpoint to apply changes:
```bash
curl http://localhost:8000/force_update
```
Adjust the URL/port if your app runs on something other than localhost:8000.

### Step 5: Enjoy
Play around with the app. Check out docs/ for additional info.
