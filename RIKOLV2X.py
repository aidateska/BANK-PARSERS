import pdfplumber
import re

# -------------------- FUNCTION FOR EXTRACTING PDF DATA --------------------
def extract_transactions_from_pdf(pdf_file):
    transactions = []
    found_initial_balance = False
    stop_processing = False

    try:
        with pdfplumber.open(pdf_file) as pdf:
            for page in pdf.pages:
                tables = page.extract_tables()

                for table in tables:
                    for row in table:
                        if not found_initial_balance:
                            if any(cell and ("Начальный остаток" in cell or "Sākuma atlikums" in cell) for cell in row):
                                found_initial_balance = True
                            continue  

                        if any(cell and ("Итого исходящие:" in cell or "Kopā izejošie:" in cell) for cell in row):
                            stop_processing = True
                            break  

                        if stop_processing:
                            break  

                        if len(row) >= 3:
                            date = row[0].strip() if row[0] else ""
                            beneficiary = " ".join(row[1].strip().split()) if row[1] else ""
                            details = " ".join(row[2].strip().split()) if row[2] else ""
                            
                            amount = ''
                            cdt_dbt_ind = ''
                            
                            possible_amount1 = row[3].strip() if len(row) > 3 and row[3] else ''
                            possible_amount2 = row[4].strip() if len(row) > 4 and row[4] else ''

                            if possible_amount1 and possible_amount2:
                                if row.index(possible_amount1) < row.index(possible_amount2):
                                    amount = possible_amount1
                                    cdt_dbt_ind = 'DBIT'
                                else:
                                    amount = possible_amount2
                                    cdt_dbt_ind = 'CRDT'
                            elif possible_amount1:
                                amount = possible_amount1
                                cdt_dbt_ind = 'DBIT'
                            elif possible_amount2:
                                amount = possible_amount2
                                cdt_dbt_ind = 'CRDT'
                            
                            if amount:
                                transactions.append({
                                    "transaction_id": "",  
                                    "date": date,
                                    "beneficiary": beneficiary,
                                    "details": details,
                                    "amount": amount,
                                    "balance": "",  
                                    "cdt_dbt_ind": cdt_dbt_ind
                                })
                    
                    if stop_processing:
                        break  

    except FileNotFoundError:
        return None
    except Exception:
        return None

    return transactions

def extract_pdf_data(pdf_file):
    try:
        with pdfplumber.open(pdf_file) as pdf:
            text = "".join([page.extract_text() for page in pdf.pages])
            
            if "RIKOLV2X" not in text:
                return None

            account_holder_match = re.search(r"(Обзор счета|Konta pārskats)\s+(.+?)\s+\d", text)
            account_holder_id_match = re.search(r"(\d{6}-\d{5})", text)
            account_number_match = re.search(r"(Счет:|Konts:)\s+(LV\d{2}RIKO\d{13})", text)
            statement_period_match = re.search(r"(Отчетный период:|Pārskata periods:)\s+(\d{2}\.\d{2}\.\d{4}\s+-\s+\d{2}\.\d{2}\.\d{4})", text)

            account_holder = account_holder_match.group(2) if account_holder_match else ""
            account_holder_id = account_holder_id_match.group(1) if account_holder_id_match else ""
            account_number = account_number_match.group(2) if account_number_match else ""
            statement_period = statement_period_match.group(2) if statement_period_match else ""

            initial_balance_match = re.search(r"(Начальный остаток|Sākuma atlikums):\s+\+?([\d,\.]+)\s+EUR", text)
            initial_balance = initial_balance_match.group(2) if initial_balance_match else ""

            transactions = extract_transactions_from_pdf(pdf_file)

            data = {
                "account_holder": account_holder,
                "account_holder_id": account_holder_id,
                "account_holder_address": "",
                "account_number": account_number,
                "statement_period": statement_period,
                "bank_name": "Luminor Bank AS",
                "bank_address": "",
                "bank_reg_no": "",
                "bank_vat_code": "",
                "bank_registration_date": "",
                "bank_bic": "RIKOLV2X",
                "transactions": transactions,
                "initial_balance": initial_balance
            }

            return data

    except FileNotFoundError:
        return None
    except Exception:
        return None

# -------------------- FUNCTION FOR EXTRACTING PDF DATA --------------------

# Automatically trigger processing when this script is run directly
if __name__ == "__main__":
    from common_script import process_files
    process_files(extract_pdf_data)
