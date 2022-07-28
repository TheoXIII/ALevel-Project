FROM python:3.10
EXPOSE 5000
WORKDIR /usr/src/app


COPY requirements.txt ./
RUN pip3 install --no-cache-dir --upgrade pip
RUN pip3 install --no-cache-dir -r requirements.txt

ENV SECRET_KEY="123"
ENV SESSION_TYPE="redis"
ENV FLASK_APP="/app/wsgi.py"
ENV SQLALCHEMY_DATABASE_URI="postgresql+psycopg2://admin:123@postgres:5432/accounts"
ENV SESSION_REDIS="redis://redis:6379"


COPY . .

CMD [ "python", "-m", "flask", "run", "--host=0.0.0.0"]
