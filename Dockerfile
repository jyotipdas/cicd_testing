FROM alpine:3.5
WORKDIR /src
RUN apk add --update python py-pip
COPY requirments.txt /src/
RUN pip install -r /src/requirments.txt
COPY main.py /src
COPY static /src
COPY templates /src
COPY leave.db /src
COPY Add_leave_everymonth_DB.py /src
CMD python /src/main.py
