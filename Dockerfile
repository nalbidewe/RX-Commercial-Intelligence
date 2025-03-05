FROM python:3.11.10

WORKDIR /project

# Copy everything at once
COPY . /project

RUN python -m pip install -r /project/requirements.txt

ENV PYTHONPATH=/project

RUN chmod -R 0744 /project

CMD ["python","-m","chainlit", "run","app.py", "-w", "--host", "0.0.0.0"]

EXPOSE 8000
