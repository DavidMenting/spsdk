#!/usr/bin/env python
# -*- coding: UTF-8 -*-
#
# Copyright 2021-2023 NXP
#
# SPDX-License-Identifier: BSD-3-Clause

"""NXP Certificate Generator."""
import logging
import os
import sys

import click
from click_option_group import optgroup

from spsdk import SPSDK_DATA_FOLDER
from spsdk.apps.utils import spsdk_logger
from spsdk.apps.utils.common_cli_options import (
    CommandsTreeGroup,
    spsdk_apps_common_options,
    spsdk_config_option,
    spsdk_output_option,
)
from spsdk.apps.utils.utils import SPSDKAppError, catch_spsdk_error
from spsdk.crypto.certificate import Certificate, generate_name
from spsdk.crypto.hash import EnumHashAlgorithm
from spsdk.crypto.keys import PrivateKey, PublicKey, PublicKeyEcc
from spsdk.crypto.types import SPSDKEncoding
from spsdk.crypto.utils import extract_public_key
from spsdk.exceptions import SPSDKError
from spsdk.utils.misc import find_file, load_configuration, load_text, write_file

NXPCERTGEN_DATA_FOLDER: str = os.path.join(SPSDK_DATA_FOLDER, "nxpcertgen")

logger = logging.getLogger(__name__)


class CertificateParametersConfig:  # pylint: disable=too-few-public-methods
    """Configuration object for creating the certificate."""

    def __init__(self, config_data: dict) -> None:
        """Initialize cert_config from yml config data."""
        try:
            self.issuer_private_key = config_data["issuer_private_key"]
            self.subject_public_key = config_data["subject_public_key"]
            self.serial_number = config_data["serial_number"]
            self.duration = config_data["duration"]
            self.basic_constrains_ca = config_data["extensions"]["BASIC_CONSTRAINTS"]["ca"]
            self.basic_constrains_path_length = config_data["extensions"]["BASIC_CONSTRAINTS"][
                "path_length"
            ]
            self.issuer_name = generate_name(config_data["issuer"])
            self.subject_name = generate_name(config_data["subject"])
        except KeyError as e:
            raise SPSDKError(f"Error found in configuration: {e} not found") from e


@click.group(name="nxpcertgen", no_args_is_help=True, cls=CommandsTreeGroup)
@spsdk_apps_common_options
def main(log_level: int) -> None:
    """Utility for certificate generation.

    !!! The NXPCERTGEN tool is deprecated, use new NXPCRYPTO tool from SPSDK for new projects !!!
    """
    click.secho("Deprecated tool! Use npxcrypto instead", fg="yellow")
    spsdk_logger.install(level=log_level, logger=logger)


@main.command(name="generate", no_args_is_help=True)
@spsdk_config_option(required=True)
@spsdk_output_option(force=True)
@click.option(
    "-e",
    "--encoding",
    required=False,
    type=click.Choice(["PEM", "DER"], case_sensitive=False),
    default="PEM",
    help="Encoding type. Default is PEM",
)
def generate(config: str, output: str, encoding: str) -> None:
    """Generate certificate.

    The configuration template files could be generated by subcommand 'get-template'.
    """
    logger.info("Generating Certificate...")
    logger.info("Loading configuration from yml file...")

    config_data = load_configuration(config)
    cert_config = CertificateParametersConfig(config_data)
    search_paths = [os.path.dirname(config)]

    priv_key = PrivateKey.load(find_file(cert_config.issuer_private_key, search_paths=search_paths))
    pub_key = PublicKey.load(find_file(cert_config.subject_public_key, search_paths=search_paths))

    certificate = Certificate.generate_certificate(
        subject=cert_config.subject_name,
        issuer=cert_config.issuer_name,
        subject_public_key=pub_key,
        issuer_private_key=priv_key,
        serial_number=cert_config.serial_number,
        duration=cert_config.duration,
        if_ca=cert_config.basic_constrains_ca,
        path_length=cert_config.basic_constrains_path_length,
    )
    logger.info("Saving the generated certificate to the specified path...")
    encoding_type = SPSDKEncoding.PEM if encoding.lower() == "pem" else SPSDKEncoding.DER
    certificate.save(output, encoding_type=encoding_type)
    logger.info("Certificate generated successfully...")
    click.echo(f"The certificate file has been created: {output}")


@main.command(name="get-template", no_args_is_help=True)
@spsdk_output_option(force=True)
def get_template(output: str) -> None:
    """Generate the template of Certificate generation YML configuration file."""
    logger.info("Creating Certificate template...")
    write_file(load_text(os.path.join(NXPCERTGEN_DATA_FOLDER, "certgen_config.yaml")), output)
    click.echo(f"The configuration template file has been created: {output}")


@main.command(name="verify", no_args_is_help=True)
@click.option(
    "-c",
    "--certificate",
    type=click.Path(exists=True, dir_okay=False),
    required=True,
    help="Path to certificate to verify",
)
@optgroup.group("Type of verification")
@optgroup.option(
    "-s",
    "--sign",
    type=click.Path(exists=True, dir_okay=False),
    help="Path to key to verify certificate signature",
)
@optgroup.option(
    "-p",
    "--puk",
    type=click.Path(exists=True, dir_okay=False),
    help="Path to key to verify public key in certificate",
)
def verify(certificate: str, sign: str, puk: str) -> None:
    """Verify signature or public key in certificate."""
    logger.info(f"Loading certificate from: {certificate}")
    cert = Certificate.load(certificate)
    if sign:
        logger.info("Performing signature verification")
        sign_algorithm = cert.signature_algorithm_oid._name
        logger.debug(f"Signature algorithm: {sign_algorithm}")
        if "ecdsa" not in sign_algorithm:
            raise SPSDKAppError(
                f"Unsupported signature algorithm: {sign_algorithm}. "
                "Only ECDSA signatures are currently supported."
            )
        verification_key = extract_public_key(sign)
        if not isinstance(verification_key, PublicKeyEcc):
            raise SPSDKError("Currently only ECC keys are supported.")
        if not cert.signature_hash_algorithm:
            raise SPSDKError("Certificate doesn't contain info about hashing alg.")

        if not verification_key.verify_signature(
            cert.signature,
            cert.tbs_certificate_bytes,
            EnumHashAlgorithm[cert.signature_hash_algorithm.name],
        ):
            raise SPSDKAppError("Invalid signature")
        click.echo("Signature is OK")

    if puk:
        logger.info("Performing public key verification")
        cert_puk = cert.get_public_key()
        other_puk = extract_public_key(puk)
        logger.debug(f"Certificate public key: {str(cert_puk)}")
        logger.debug(f"Other public key: {str(other_puk)}")

        if cert_puk == other_puk:
            click.echo("Public key in certificate matches the input")
        else:
            raise SPSDKAppError("Public key in certificate differs from the input")


@catch_spsdk_error
def safe_main() -> None:
    """Call the main function."""
    sys.exit(main())  # pylint: disable=no-value-for-parameter


if __name__ == "__main__":
    safe_main()
