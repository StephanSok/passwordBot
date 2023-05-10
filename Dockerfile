FROM python:3.10

WORKDIR /app

COPY . .


RUN make install


CMD ["make", "run"]