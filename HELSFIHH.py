import pdfplumber
import re

# -------------------- FUNCTION FOR EXTRACTING TRANSACTIONS --------------------
def extract_transactions_from_pdf(pdf_file):
    transactions = []
    transaction_id = 1
    transaction_pattern = re.compile(
        r'(?P<beneficiary>[A-Z0-9]+) [A-Z] (?P<date>\d{4}) (?P<details>.+?) (?P<amount>\d+\.\d{2}) (?P<cdt_dbt_ind>[\+-])'
    )
    
    with pdfplumber.open(pdf_file) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            lines = text.split("\n")
            
            for line in lines:
                match = transaction_pattern.search(line)
                if match:
                    trans_data = match.groupdict()
                    
                    
                    trans_data["transaction_id"] = f'{transaction_id:03}'
                    
                    
                    date = trans_data["date"]
                    trans_data["date"] = f"{date[:2]}/{date[2:]}"
                    
                    
                    trans_data["cdt_dbt_ind"] = "CRDT" if trans_data["cdt_dbt_ind"] == '+' else "DBIT"
                    
                    transactions.append(trans_data)
                    transaction_id += 1

    return transactions

def extract_pdf_data(pdf_file):
    try:
        with pdfplumber.open(pdf_file) as pdf:
            text = "".join([page.extract_text() for page in pdf.pages])
            
            if "HELSFIHH" not in text:
                
                return None

            lines = text.split('\n')
            account_info = {}
            
            
            line_3 = lines[3]
            account_info["statement_date"], account_info["account_number"] = re.split(r'\s+', line_3.strip(), maxsplit=1)
            account_info["account_number"] = account_info["account_number"].strip()

            account_info["account_holder_address"] = lines[4].strip()

            line_5 = lines[5]
            match = re.search(r'PUH\.\s+(\d{3}\s+\d{3}\s+\d{3})\s+Kausi', line_5)
            if match:
                account_info["account_holder_id"] = match.group(1).strip()

            period_match = re.search(r'(\d{2}\.\d{2}\.\d{4} - \d{2}\.\d{2}\.\d{4})', lines[6])
            if period_match:
                account_info["statement_period"] = period_match.group(1)

            account_info["bank_name"] = "Aktia Pankki Oyj"
            account_info["bank_address"] = "Arkadiankatu 4-6, 00100 Helsinki"
            account_info["bank_reg_no"] = "2181702-8"
            account_info["bank_vat_code"] = "FI21817028"
            account_info["bank_bic"] = "HELSFIHH"

            
            saldo_index = next((i for i, line in enumerate(lines) if "SALDO" in line), None)
            if saldo_index is not None:
                saldo_line = lines[saldo_index]
                saldo_date_match = re.search(r'SALDO (\d{2}\.\d{2}\.\d{4})', saldo_line)
                if saldo_date_match:
                    saldo_date = saldo_date_match.group(1)
                    if saldo_date == account_info["statement_period"].split(" - ")[0]:
                        initial_balance = saldo_line.split(saldo_date)[1].strip()
                        
                        if initial_balance.startswith('-'):
                            initial_balance = initial_balance[1:].strip()
                        account_info["initial_balance"] = initial_balance

            
            closing_balance_index = next((i for i, line in enumerate(lines) if "NOSTETTAVISSA" in line), None)
            if closing_balance_index is not None:
                closing_balance_line = lines[closing_balance_index]
                closing_balance_match = re.search(r'NOSTETTAVISSA\s+([\d\.,]+)', closing_balance_line)
                if closing_balance_match:
                    account_info["closing_balance"] = closing_balance_match.group(1).strip()

            data = {
                "account_holder": "",  
                "account_holder_id": account_info.get("account_holder_id", ""),
                "account_holder_address": account_info.get("account_holder_address", ""),
                "account_number": account_info.get("account_number", ""),
                "statement_period": account_info.get("statement_period", ""),
                "bank_name": account_info.get("bank_name", ""),
                "bank_address": account_info.get("bank_address", ""),
                "bank_reg_no": account_info.get("bank_reg_no", ""),
                "bank_vat_code": account_info.get("bank_vat_code", ""),
                "bank_registration_date": "",  
                "bank_bic": account_info.get("bank_bic", ""),
                "transactions": extract_transactions_from_pdf(pdf_file),
                "initial_balance": account_info.get("initial_balance", ""),
                "closing_balance": account_info.get("closing_balance", "")
            }

            return data

    except Exception:
       
        return None

# -------------------- FUNCTION FOR PROCESSING FILES --------------------
def process_files(extract_function):
    import os

    pdf_files = [f for f in os.listdir('.') if f.endswith('.pdf')]
    results = []
    
    for pdf_file in pdf_files:
        data = extract_function(pdf_file)
        if data:
            results.append(data)
    
    return results

# -------------------- MAIN EXECUTION --------------------
if __name__ == "__main__":
    process_files(extract_pdf_data)
