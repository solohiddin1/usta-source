FROM python:3.12-alpine
WORKDIR /app
RUN apk add --no-cache bash busybox-suid

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN chmod +x /app/task.sh
RUN echo "0 0 * * * /app/task.sh >> /app/task.log 2>&1" > /etc/crontabs/root

EXPOSE 8000

CMD ["sh", "-c", "crond && python manage.py migrate && python manage.py runserver 0.0.0.0:8000"]