import pdfplumber
import re

# -------------------- FUNCTION FOR EXTRACTING PDF DATA --------------------
def extract_pdf_data(pdf_path):
    data = {
        "statement_date": "",
        "account_holder": "",
        "account_holder_address": "",
        "account_number": "",
        "statement_period": "",
        "bank_name": "",
        "bank_bic": "ITELFIHH",
        "bank_reg_no": "0104239000",
        "bank_address": "HUVUDKONTOR NÄRPES NÄRPESVÄGEN 13",
        "initial_balance": "",  # Changed from opening_balance to initial_balance
        "transactions": []
    }

    try:
        with pdfplumber.open(pdf_path) as pdf:
            text = "".join([page.extract_text() for page in pdf.pages])
            
            if "ITELFIHH" not in text:
                return None

            extracting_transactions = False
            transaction_id = 0
            transaction_details = ""
            skip_header = False

            for page in pdf.pages:
                text = page.extract_text() or ""

                if not extracting_transactions:
                    statement_date_match = re.search(r"AB\s+(\d{2}\.\d{2}\.\d{4})", text)
                    if statement_date_match:
                        data["statement_date"] = statement_date_match.group(1)

                    bank_name_match = re.search(r"NÄRPES\s+(.*?)\s+AB", text)
                    if bank_name_match:
                        data["bank_name"] = bank_name_match.group(1)

                    account_info_match = re.search(r"Mottagare\s+IBAN-kontonummer\s+(.*?)\s+FI(\d{2}\s+\d{4}\s+\d{4}\s+\d{4}\s+\d{2})(.*?)\s+BIC-kod", text, re.DOTALL)
                    if account_info_match:
                        account_info = account_info_match.group(1).strip()
                        account_number = account_info_match.group(2).replace(" ", "")
                        address_info = account_info_match.group(3).strip()

                        data["account_holder"] = account_info.split('\n')[0].strip()
                        data["account_number"] = f"FI{account_number}"
                        data["account_holder_address"] = ' '.join(address_info.split('\n')).strip()

                    statement_period_match = re.search(r"NÄRPESVÄGEN 13\s+(\d{2}\.\d{2}\.\d{4}) - (\d{2}\.\d{2}\.\d{4})", text)
                    if statement_period_match:
                        start_date = statement_period_match.group(1)
                        end_date = statement_period_match.group(2)
                        data["statement_period"] = f"{start_date} - {end_date}"

                    initial_balance_match = re.search(r"SALDO\s+(\d{2}\.\d{2}\.\d{4})\s+([+-]?\d{1,3}(?:\.\d{3})*,\d{2})", text)
                    if initial_balance_match:
                        data["initial_balance"] = initial_balance_match.group(2).replace(",", ".")

                    if "BetalningsdagValördag Förklaring EUR" in text:
                        extracting_transactions = True
                        continue

                if extracting_transactions:
                    if skip_header:
                        lines = text.split('\n')
                        for i, line in enumerate(lines):
                            if re.search(r"\d{2}\.\d{2}\.\d{4}\s+-\s+\d{2}\.\d{2}\.\d{4}", line):
                                transaction_lines = lines[i + 1:]
                                break
                        skip_header = False
                    else:
                        transaction_lines = text.split('\n')

                    for line in transaction_lines:
                        date_match = re.match(r"\d{2}\.\d{2}", line)
                        if date_match:
                            date = date_match.group(0)
                            if transaction_details and data["transactions"]:
                                arn_index = transaction_details.find("ARN:")
                                if arn_index != -1:
                                    transaction_details = transaction_details[:arn_index].strip()
                                data["transactions"][-1]["details"] = transaction_details.strip()

                            transaction_details = ""
                            transaction_id += 1
                            transaction_parts = line.split()
                            amount_index = -1
                            for i in range(len(transaction_parts) - 1, 0, -1):
                                if re.match(r"^[+-]?\d+(,\d{3})*,\d+$", transaction_parts[i]):
                                    amount_index = i
                                    break
                            if amount_index == -1:
                                continue
                            amount = transaction_parts[amount_index].replace(",", ".")

                            beneficiary_parts = transaction_parts[1:amount_index]
                            if beneficiary_parts[-1].endswith("/A") or re.match(r"\d{2}\.\d{2}", beneficiary_parts[-1]):
                                beneficiary_parts.pop()
                            beneficiary = " ".join(beneficiary_parts).strip()

                            cdt_dbt_ind = "CRDT" if amount.startswith("+") else "DBIT"

                            data["transactions"].append({
                                "transaction_id": f"{transaction_id:03d}",
                                "date": date,
                                "beneficiary": beneficiary,
                                "details": "",
                                "amount": amount,
                                "balance": "",
                                "cdt_dbt_ind": cdt_dbt_ind
                            })
                        else:
                            transaction_details += f" {line.strip()}"

                    skip_header = True

            if transaction_details and data["transactions"]:
                arn_index = transaction_details.find("ARN:")
                if arn_index != -1:
                    transaction_details = transaction_details[:arn_index].strip()
                data["transactions"][-1]["details"] = transaction_details.strip()

            for transaction in data["transactions"]:
                if re.match(r"\d{2}\.\d{2}", transaction["beneficiary"]):
                    transaction["beneficiary"] = " ".join(transaction["beneficiary"].split()[1:])

            return data

    except Exception:
        return None

# -------------------- FUNCTION FOR EXTRACTING PDF DATA --------------------

# Automatically trigger processing when this script is run directly
if __name__ == "__main__":
    from common_script import process_files
    process_files(extract_pdf_data)
