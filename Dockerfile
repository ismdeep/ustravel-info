FROM python:3.8

MAINTAINER L. Jiang <l.jiang.1024@gmail.com>

RUN mkdir -p /ustravel-info
ADD .        /ustravel-info
RUN mkdir -p /root/.pip
COPY pip.conf /root/.pip/

WORKDIR /ustravel-info
RUN pip install -r requirements.txt

CMD ["python", "main.py", "/data"]