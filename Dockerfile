FROM python:3.13-slim


# Step 2: Set the working directory in the container
WORKDIR /app

# Step 3: Copy the requirements file into the container
COPY requirements.txt /app/

# Step 4: Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Step 5: Copy the rest of the application code into the container
COPY . /app/

# Step 6: Expose the port that the app will run on
EXPOSE 5000

# Step 7: Set environment variables (optional, if needed)
ENV FLASK_APP=app.py

# Step 8: Run the application
#CMD ["python", "app.py"]
CMD ["gunicorn","-k","eventlet","-w","1","-b","0.0.0.0:5000","app:app"]

