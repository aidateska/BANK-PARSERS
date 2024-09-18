import pdfplumber
import re
from datetime import datetime

# Funkcija za parsiranje transakcija
def parse_transactions(text):
    transactions = []
    lines = text.split('\n')
    transaction_id = 1
    transaction = None
    date_pattern = re.compile(r'\d{2}\.\d{2}\.\d{2}')  
    amount_pattern = re.compile(r'([+-]\s?\d{1,3}(?:\s?\d{3})*,\d{2})')  

    transaction_keys = ["TILISIIRTO", "PALVELUMAKSU", "VIITESIIRTO", "PANO"]
    stop_keywords = ["SALDO", "NOSTOVARA", "OTOT YHTEENSÄ"]

    for i, line in enumerate(lines):
        if any(key in line for key in transaction_keys):
            date_match = date_pattern.search(line)
            if date_match:
                parts = line.split()
                beneficiary = parts[0] if parts else ""
                date = date_match.group()
                amount_match = amount_pattern.search(line)
                if amount_match:
                    amount_full = amount_match.group().replace(" ", "")
                    amount = amount_full[1:]  # uklanja znak
                    cdt_dbt_ind = "CRDT" if amount_full[0] == "+" else "DBIT"
                else:
                    amount = ""
                    cdt_dbt_ind = ""
                
                if transaction:  
                    transactions.append(transaction)
                
                transaction = {
                    "transaction_id": f"{transaction_id:03d}",
                    "date": date,
                    "beneficiary": beneficiary,
                    "details": "",
                    "amount": amount,
                    "balance": "",
                    "cdt_dbt_ind": cdt_dbt_ind
                }
                transaction_id += 1
            else:
                continue

        elif transaction:  
            if any(keyword in line for keyword in stop_keywords):
                transactions.append(transaction)
                transaction = None
            else:
                transaction["details"] += line + " "

    if transaction:  
        transactions.append(transaction)

    return transactions


def extract_pdf_data(pdf_path):
    data = {
        "statement_date": "",
        "account_holder": "",
        "account_holder_address": "",
        "account_number": "",
        "statement_period": "",
        "bank_name": "OP FIN",
        "bank_bic": "OKOYFIHH",
        "bank_reg_no": "0242522-1",
        "bank_address": "Gebhardinaukio 1, Helsinki",
        "initial_balance": "",
        "closing_balance": "",
        "transactions": []
    }

    try:
        statement_date_pattern = re.compile(r'(\d{1,2})\.(\d{1,2})\.(\d{4})')
        account_number_pattern = re.compile(r'Tilinumero IBAN:\s+([A-Z]+\d{2}\s+\d{4}\s+\d{4}\s+\d{4}\s+\d{2})\s+BIC:')
        initial_balance_pattern = re.compile(r'SALDO\s+\d{1,2}\.\d{1,2}\.\d{4}\s+([+-]\s?\d{1,3}(?:\s?\d{3})*,\d{2})')
        closing_balance_pattern = re.compile(r'SALDO\s+\d{1,2}\.\d{1,2}\.\d{4}\s+([+-]\s?\d{1,3}(?:\s?\d{3})*,\d{2})')

        current_year = datetime.now().year

        with pdfplumber.open(pdf_path) as pdf:
            text = "".join([page.extract_text() for page in pdf.pages])
            
            if "OKOYFIHH" not in text:
                return None

            statement_date_match = statement_date_pattern.search(text)
            if statement_date_match:
                day, month, year = statement_date_match.groups()
                data["statement_date"] = f"{day.zfill(2)}.{month.zfill(2)}.{year.zfill(4)}"

            account_number_match = account_number_pattern.search(text)
            if account_number_match:
                data["account_number"] = account_number_match.group(1).replace(" ", "")

            initial_balance_match = initial_balance_pattern.search(text)
            if initial_balance_match:
                data["initial_balance"] = initial_balance_match.group(1).replace(' ', '')

            closing_balance_matches = closing_balance_pattern.findall(text)
            if closing_balance_matches:
                data["closing_balance"] = closing_balance_matches[-1].replace(' ', '')

            # Parsiranje perioda izvoda
            lines = text.split('\n')
            if len(lines) >= 2:
                statement_period_line = lines[1].replace("Ajalta", "").strip()
                data["statement_period"] = statement_period_line

            for i, line in enumerate(lines):
                if 'Ajalta' in line:
                    if (i + 2) < len(lines):
                        data['account_holder'] = lines[i + 2].strip()
                    if (i + 3) < len(lines):
                        data['account_holder_address'] = lines[i + 3].strip()
                    break

            
            data["transactions"] = parse_transactions(text)

    except Exception:
        
        return None

    return data


if __name__ == "__main__":
    from common_script import process_files
    process_files(extract_pdf_data)
