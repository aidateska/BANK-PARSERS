import pdfplumber
import re

# -------------------- FUNCTION FOR EXTRACTING PDF DATA --------------------
def extract_pdf_data(pdf_path):
    try:
        with pdfplumber.open(pdf_path) as pdf:
            text = "".join([page.extract_text() for page in pdf.pages])
            
            
            if 'AS "Citadele banka" Reģ.' not in text:
                return None

            data = {
                "account_holder": "",
                "account_holder_id": "",
                "account_holder_address": "",
                "account_number": "",
                "statement_period": "",
                "bank_name": "AS Citadele banka",
                "bank_address": "Republikas laukums 2A",
                "bank_reg_no": "40103303559",
                "bank_vat_code": "",
                "bank_registration_date": "",
                "bank_bic": "PARXLV22",
                "initial_balance": "",
                "transactions": []
            }

            
            account_holder_match = re.search(r"Konta pārskats\s*(.*?)\s*Personas kods/Pases Nr\.", text, re.MULTILINE | re.DOTALL)
            if account_holder_match:
                data["account_holder"] = account_holder_match.group(1).strip()

            
            index = text.find("Personas kods/Pases Nr.:")
            if index != -1:
                segment = text[index:]
                account_holder_id_match = re.search(r"Personas kods/Pases Nr\.\s*(\d{6}-\d{5})", segment)
                if account_holder_id_match:
                    data["account_holder_id"] = account_holder_id_match.group(1)
                    
                address_start = segment.find(data["account_holder_id"]) + len(data["account_holder_id"]) + len("Personas kods/Pases Nr.: ")
                address_segment = segment[address_start:]
                address_end = address_segment.find("Konta numurs (IBAN):")
                if address_end != -1:
                    address_text = address_segment[:address_end].strip().split("\n", 1)
                    data["account_holder_address"] = address_text[1].strip() if len(address_text) > 1 else ""
                else:
                    data["account_holder_address"] = address_segment.strip()
                
                text = text.replace(f"Personas kods/Pases Nr.: {data['account_holder_id']}", "")
                text = text.replace(data["account_holder_address"], "")
            else:
                data["account_holder_id"] = ""
                data["account_holder_address"] = ""

           
            account_number_match = re.search(r"Konta numurs \(IBAN\):\s*(LV\d{2}[A-Z0-9]{15})", text)
            if account_number_match:
                data["account_number"] = account_number_match.group(1).replace(" ", "")

            
            statement_period_match = re.search(r"No\s+(\d{2}\.\d{2}\.\d{4})\s+līdz\s+(\d{2}\.\d{2}\.\d{4})", text)
            if statement_period_match:
                data["statement_period"] = f"{statement_period_match.group(1)} - {statement_period_match.group(2)}"

            
            initial_balance_match = re.search(r"Sākuma atlikums:\s*([\d,\.]+)", text)
            if initial_balance_match:
                data["initial_balance"] = initial_balance_match.group(1).replace(' ', '')

            
            data["transactions"] = extract_transactions_from_pdf(pdf_path)

            return data

    except Exception:
       
        return None

def extract_transactions_from_pdf(pdf_file):
    transactions = []
    found_initial_balance = False
    stop_processing = False

    with pdfplumber.open(pdf_file) as pdf:
        for page in pdf.pages:
            tables = page.extract_tables()

            initial_balance = ""
            found_initial_balance = False
            stop_processing = False
            
            for table in tables:
                for row in table:
                    if not found_initial_balance:
                        
                        for cell in row:
                            if cell and "Sākuma atlikums" in cell:
                                initial_balance = cell.split("Sākuma atlikums:")[-1].strip()
                                found_initial_balance = True
                                break
                        if found_initial_balance:
                            continue
            
                    
                    if any(cell and ("Izejošie maksājumi" in cell or "Debeta apgrozījums" in cell) for cell in row):
                        stop_processing = True
                        break
            
                    if stop_processing:
                        break

                    if len(row) >= 2:
                        
                        if is_date(row[0]):
                            date = row[0].strip()
                            beneficiary = row[1].strip() if len(row) > 1 else ""
                            details = row[2].strip() if len(row) > 2 else ""
                        elif is_date(row[1]):
                            date = row[1].strip()
                            beneficiary = row[2].strip() if len(row) > 2 else ""
                            details = row[3].strip() if len(row) > 3 else ""
                        else:
                            continue  
                        
                        
                        possible_amount = row[-1].strip() if len(row) > 1 and row[-1] else ''
                        if not possible_amount:
                            possible_amount = row[-2].strip() if len(row) > 2 and row[-2] else ''
                        
                        if possible_amount.startswith('+'):
                            amount = possible_amount[1:].strip()
                            cdt_dbt_ind = 'CRDT'
                        elif possible_amount.startswith('-'):
                            amount = possible_amount[1:].strip()
                            cdt_dbt_ind = 'DBIT'
                        else:
                            amount = ''
                            cdt_dbt_ind = ''

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

    return transactions

def is_date(value):
    
    return bool(re.match(r'\d{2}\.\d{2}\.\d{4}', value))

# -------------------- FUNCTION FOR EXTRACTING PDF DATA --------------------

# Automatically trigger processing when this script is run directly
if __name__ == "__main__":
    from common_script import process_files
    process_files(extract_pdf_data)
