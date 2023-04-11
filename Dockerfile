FROM python:3.8

VOLUME ["/data"]

ADD . /work

WORKDIR /work

RUN pip install pipenv

RUN pipenv install --deploy

CMD /bin/bash -c 'pipenv run server'