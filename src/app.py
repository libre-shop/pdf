import html
import time
from enum import Enum
from flask import Flask, request, send_file, jsonify
from prometheus_flask_exporter import PrometheusMetrics
import subprocess
import tempfile
import os
import re
import json
import yaml
from typing import List, NamedTuple
import logging


class FilterRemoveDate(logging.Filter):
    # '192.168.0.102 - - [30/Jun/2024 01:14:03] "%s" %s %s' -> '192.168.0.102 - "%s" %s %s'
    pattern: re.Pattern = re.compile(r' - \[.+?]')

    def filter(self, record: logging.LogRecord) -> bool:
        record.msg = self.pattern.sub('', record.msg)
        return True

class FilterReplaceWerkzeug(logging.Filter):
    # 'werkzeug:' -> 'app:flask:'
    pattern: re.Pattern = re.compile(r'werkzeug:')

    def filter(self, record: logging.LogRecord) -> bool:
        record.msg = self.pattern.sub('app:flask:', record.msg)
        return True

class FilterReplaceLowercaseI(logging.Filter):
    # 'I:' -> 'i:'
    pattern: re.Pattern = re.compile(r'I:')

    def filter(self, record: logging.LogRecord) -> bool:
        record.msg = self.pattern.sub('i:', record.msg)
        return True

# Setup logger
logging.basicConfig(
	level=logging.DEBUG,
	format='%(asctime)s.%(msecs)03dZ %(name)s:%(levelname).1s: %(message)s',
	datefmt='%Y-%m-%d %H:%M:%S'
)

logger = logging.getLogger('app')
logger_werkzeug = logging.getLogger('werkzeug')
logger_werkzeug.addFilter(FilterRemoveDate())
logger_werkzeug.addFilter(FilterReplaceWerkzeug())
logger_werkzeug.addFilter(FilterReplaceLowercaseI())

app = Flask(__name__, static_folder=None)

metrics = PrometheusMetrics(app, defaults_prefix="pdf")

# Define a counter for successful pdf generation
pdf_generation_counter = metrics.counter(
	'pdf_generation_total',
	'Total number of pdfs generated',
	labels={'endpoint': lambda: request.endpoint}
)


class Template(Enum):
	INVOICE = "/app/data/templates/invoice-scrlttr2.tex"
	INVOICE_EXAMPLE = "/app/data/templates/invoice-scrlttr2.example.tex"
	SHIPPING = "/app/data/templates/shipping-note-scrlttr2.tex"
	ORDER_CONFIRMATION = "/app/data/templates/order-confirmation.tex"
	LETTERHEAD = "/app/data/templates/RE.pdf"
	DETAILS = ""

template_to_label = {
    Template.INVOICE: "invoice",
    Template.SHIPPING: "shipping",
    Template.ORDER_CONFIRMATION: "order_confirmation"
}

class SenderAddress(NamedTuple):
	companyname: str
	name: str
	street: str
	city: str
	email: str
	url: str


class RecipientAddress(NamedTuple):
	name: str
	address: List[str]


class Services(NamedTuple):
	description: str
	price: float
	details: List[str]


class Details(NamedTuple):
	subject: str
	date: str
	me: SenderAddress
	to: RecipientAddress
	invoice_nr: str
	author: str
	city: str
	VAT: int
	service: List[Services]
	closingnote: str


def normalize(string: str):
	return (
		string
		.lower()
		.replace('ö', 'oe')
		.replace('ä', 'ae')
		.replace('ß', 'ss')
		.replace('ü', 'ue')
		.replace(',', '')
		.replace('.', '')
		.replace(' ', '')
	)


def generate_pdf(template_path: Template, details_json: Details):
	try:
		logger = logging.getLogger('app:generate-pdf')
		logger.info("Generating pdf")
		logger.debug(details_json)
		details_dict = json.loads(json.dumps(details_json))
		details_yaml = yaml.dump(details_dict)
		date = time.strftime("%Y%m%d")
		label = template_to_label[template_path]

		logger.debug(details_yaml)

		with tempfile.TemporaryDirectory() as temp_dir:
			# Write the details JSON to a YAML file
			details_yaml_path = os.path.join(temp_dir, 'details.md')

			with open(details_yaml_path, 'w') as yaml_file:
				yaml_file.write("---\n")
				yaml_file.write("letterhead: /app/data/templates/RE.pdf\n")
				yaml_file.write(details_yaml)
				yaml_file.write("...\n")
				yaml_file.write(details_dict["body"])

			normalized_recipient = normalize(details_dict["to"]["name"] or details_dict["to"]["address"][0])
			output_base_path = os.path.join("/", "app", "data", "output", f'{date}-{label}-{normalized_recipient}')

			logger.debug(normalized_recipient)

			counter = 0
			if os.path.exists(output_base_path + '.pdf'):
				counter = 1
				while os.path.exists(f'{output_base_path}-{counter}.pdf'):
					counter += 1
				output_path = f'{output_base_path}-{counter}.pdf'
			else:
				output_path = output_base_path + '.pdf'

			logger.debug(f"Starting Pandoc")
			logger.debug(f"Source YAML: {details_yaml_path}")
			logger.debug(f"Template: {template_path.value}")
			logger.debug(f"Output pdf: {output_path}")

			result = subprocess.run([
				'make',
				'-e',
				'-B',
				f'src={details_yaml_path}',
				f'template={template_path.value}',
				f'output={output_path}'
			])

			if result.returncode != 0:
				logger.error(f"Pdf generation failed: {result.stderr}")
				return None

			logger.info("Pdf generated successfully")
			return output_path

	except Exception as e:
		logger.error(f"Error generating pdf: {str(e)}")
		return None


@app.route('/v1')
@metrics.do_not_track()
def info():
	today = time.strftime("%Y-%m-%d")
	url_map = app.url_map
	return f"<h1>pdf v1.0.0 - {today}</h1><pre>" + html.escape(str(url_map), False) + "</pre>"


@app.route('/v1/invoice', methods=['POST'])
@pdf_generation_counter
def generate_invoice():
	logger = logging.getLogger('app:generate-invoice')
	try:
		details_json = request.json
		logger.info("Generating invoice")
		logger.debug(details_json)
		template = Template.INVOICE
		pdf_content = generate_pdf(template, details_json)
		if pdf_content:
			logger.info(f"Sending invoice pdf: {pdf_content}")
			return send_file(pdf_content, mimetype='application/pdf')
		else:
			logger.error("Sending pdf failed")
			return jsonify({"status": "failed"}), 500
	except Exception as e:
		logger.error(f"Error in generate_invoice: {str(e)}")
		return jsonify({"status": "failed"}), 500


@app.route('/v1/shipping', methods=['POST'])
@pdf_generation_counter
def generate_shipping():
	logger = logging.getLogger('app:generate-shipping-note')
	try:
		details_json = request.json
		logger.info("Generating shipping note")
		logger.debug(details_json)
		template = Template.SHIPPING
		pdf_content = generate_pdf(template, details_json)
		if pdf_content:
			logger.info(f"Sending shipping pdf: {pdf_content}")
			return send_file(pdf_content, mimetype='application/pdf')
		else:
			logger.error("Sending pdf failed, generated pdf is empty")
			return jsonify({"status": "failed"}), 500
	except Exception as e:
		logger.error(f"Error in generate_shipping: {str(e)}")
		return jsonify({"status": "failed"}), 500


@app.route('/v1/order-confirmation', methods=['POST'])
@pdf_generation_counter
def generate_order_confirmation():
	logger = logging.getLogger('app:generate-order-confirmation')
	try:
		details_json = request.json
		logger.info("Generating order confirmation")
		logger.debug(details_json)
		template = Template.ORDER_CONFIRMATION
		pdf_content = generate_pdf(template, details_json)
		if pdf_content:
			logger.info(f"Sending order confirmation pdf: {pdf_content}")
			return send_file(pdf_content, mimetype='application/pdf')
		else:
			logger.error("pdf generation failed")
			return "pdf generation failed", 500
	except Exception as e:
		logger.error(f"Error in generate_order_confirmation: {str(e)}")
		return str(e), 400


@app.route('/v1/delete/pdf', methods=['DELETE'])
def delete_pdf():
	logger = logging.getLogger('app:delete-pdf')
	try:
		subprocess.run([
			'make',
			'-e',
			'clean'
		])
		logger.info("Cleaned up pdf files in /app/data/output directory.")
		return jsonify({"status": "success"}), 204
	except Exception as e:
		logger.error(f"Failed to clean pdf files: {str(e)}")
		return jsonify({"status": "failed"}), 500


@app.route('/v1/delete/all', methods=['DELETE'])
def delete_all():
	logger = logging.getLogger('app:delete-all-pdf')
	try:
		subprocess.run([
			'make',
			'-e',
			'cleanall'
		])
		logger.info("Cleaned up ALL files in /app/data/output directory.")
		return jsonify({"status": "success"}), 204
	except Exception as e:
		logger.error(f"Failed to clean all files: {str(e)}")
		return jsonify({"status": "failed"}), 500


@app.route('/health', methods=['GET'])
def health_check():
    logger = logging.getLogger('app:health-check')
    health_status = {'status': 'ok'}

    # Check write access to output directory
    output_dir = "/app/data/output"
    try:
        test_file = os.path.join(output_dir, "test_write.txt")
        with open(test_file, "w") as f:
            f.write("test")
        os.remove(test_file)
        health_status['output_dir_writable'] = True
    except Exception as e:
        logger.error(f"Output directory not writable: {str(e)}")
        health_status['output_dir_writable'] = False
        health_status['status'] = 'error'

    # Check if Pandoc is responding
    try:
        result = subprocess.run(['pandoc', '--version'], capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            health_status['pandoc_responding'] = True
        else:
            health_status['pandoc_responding'] = False
            health_status['status'] = 'error'
    except subprocess.TimeoutExpired:
        logger.error("Pandoc check timed out")
        health_status['pandoc_responding'] = False
        health_status['status'] = 'error'
    except Exception as e:
        logger.error(f"Error checking Pandoc: {str(e)}")
        health_status['pandoc_responding'] = False
        health_status['status'] = 'error'

    logger.debug(f"Health check performed: {health_status}")
    return jsonify(health_status)


if __name__ == '__main__':
	app.run(host='0.0.0.0', port=1111, debug=False)
