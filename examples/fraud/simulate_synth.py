import argparse
import datetime
import datetime as dt
import json
import time

import kafka
from river.datasets import synth
from river import stream
import logging


class colors:
    GREEN = "\033[92m"
    BLUE = "\033[94m"
    ENDC = "\033[0m"


if __name__ == "__main__":

    parser = argparse.ArgumentParser()
    parser.add_argument("speed", type=int, nargs="?", default=600)
    args = parser.parse_args()

    def sleep(td: dt.timedelta):
        secs = td.seconds
        if secs >= 0:
            secs = min(30, secs)
            time.sleep(secs / args.speed)

    dataset = synth.AnomalySine(seed=12345,
                             n_samples=100_000,
                             n_anomalies=25_000,
                             contextual=True,
                             n_contextual=10)

    now = datetime.datetime.now()
    predictions = {}

    # Empty topics for idempotency

    while True:
        try:
            broker_admin = kafka.admin.KafkaAdminClient(bootstrap_servers=["redpanda:29092"])
            break
        except (kafka.errors.NoBrokersAvailable):
            logging.info("Waiting for redpanda to be ready")

            time.sleep(1)

    for topic_name in ["anomaly_sine", "anomaly_labels"]:
        try:
            broker_admin.delete_topics([topic_name])
        except kafka.errors.UnknownTopicOrPartitionError:
            ...

    broker = kafka.KafkaProducer(
        bootstrap_servers=["redpanda:29092"],
        key_serializer=str.encode,
        value_serializer=lambda v: json.dumps(v).encode("utf-8"),
    )

    for i, sines, label in stream.simulate_qa(
        dataset,
        moment=lambda x: dt.datetime.now(),
        delay=dt.timedelta(seconds=5),
    ):
        sample_no = str(i).zfill(len(str(dataset.n_samples)))

        # Transaction takes place
        transaction_time = now + dt.timedelta(seconds=5)

        if label is None:

            # Wait
            sleep(transaction_time - now)
            now = transaction_time
            broker.send(
                topic="anomaly_sine",
                key=sample_no,
                value=sines
            )

            logging.debug(colors.GREEN + f"#{sample_no} happens at {now}" + colors.ENDC)
            continue

        # Transaction is labeled by a human-expert
        else:
            # Wait
            decision_time = transaction_time + dt.timedelta(seconds=10)
            sleep(decision_time - now)
            now = decision_time

        # Send the label
        broker.send(
            topic="anomaly_labels",
            key=sample_no,
            value={"target": label},
        )

        # Notify decision and compare prediction against ground truth
        # td = dt.timedelta(seconds=duration)
        logging.debug(colors.BLUE + f"#{sample_no} annotated at {now}, took {decision_time - transaction_time}" + colors.ENDC)
