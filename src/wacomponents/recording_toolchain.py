# This file is part of Witness Angel Components
# SPDX-FileCopyrightText: Copyright Prolifik SARL
# SPDX-License-Identifier: GPL-2.0-or-later

import logging

logger = logging.getLogger(__name__)


def start_recording_toolchain(toolchain):
    """
    Start all the sensors, thus ensuring that the toolchain begins to record end-to-end.
    """

    free_keys_generator_worker = toolchain["free_keys_generator_worker"]
    if free_keys_generator_worker:
        logger.info("Starting the generator of free keys")
        free_keys_generator_worker.start()
    else:
        logger.info("Ignoring the generator of free keys")

    sensors_manager = toolchain["sensors_manager"]
    sensors_manager.start()


def stop_recording_toolchain(toolchain):
    """
    Perform an ordered stop+flush of sensors and miscellaneous layers of aggregator.

    All objets remain in a usable state
    """

    # TODO push all this to sensor manager!!

    # logger.info("stop_recording_toolchain starts")

    sensors_manager = toolchain["sensors_manager"]
    data_aggregators = toolchain["data_aggregators"]
    tarfile_aggregators = toolchain["tarfile_aggregators"]
    cryptainer_storage = toolchain["cryptainer_storage"]
    free_keys_generator_worker = toolchain["free_keys_generator_worker"]

    if free_keys_generator_worker:
        logger.info("Stopping the generator of free keys")
        free_keys_generator_worker.stop()

    # logger.info("Stopping sensors manager")
    sensors_manager.stop()

    # logger.info("Joining sensors manager")
    sensors_manager.join()

    for idx, data_aggregator in enumerate(data_aggregators, start=1):
        logger.info("Flushing '%s' data aggregator", data_aggregator.sensor_name)
        data_aggregator.flush_payload()

    for idx, tarfile_aggregator in enumerate(tarfile_aggregators, start=1):
        logger.info("Flushing tarfile builder %s", " #%d" % idx if len(tarfile_aggregators) > 1 else "")
        tarfile_aggregator.finalize_tarfile()

    cryptainer_storage.wait_for_idle_state()  # Encryption workers must finish their job

    # logger.info("stop_recording_toolchain exits")
