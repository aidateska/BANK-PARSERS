import pdfplumber
import re

def extract_pdf_data(pdf_file):
    try:
        with pdfplumber.open(pdf_file) as pdf:
            if not any("HABALV22" in page.extract_text() for page in pdf.pages):
                return None

            initial_balance = None
            closing_balance = None
            transactions = []
            transaction_id = 1
            
            first_page = pdf.pages[0]
            lines = first_page.extract_text().split("\n")

            account_holder = ""
            for line in lines:
                if "AS Swedbank" in line:
                    account_holder = line.split("AS Swedbank")[0].strip()
                    break

            account_holder_id = ""
            for line in lines:
                if "p.k." in line:
                    account_holder_id = re.search(r"p\.k\.\s*(\d{6}-\d{5})", line).group(1)
                    break

            account_holder_address = lines[3].strip()

            account_number = ""
            for line in lines:
                if "Konts" in line:
                    match = re.search(r"LV\d{2} HABA \d{4} \d{4} \d{4} \d{1}", line)
                    if match:
                        account_number = match.group(0)
                    break

            statement_period = ""
            for line in lines:
                if "Periods" in line:
                    statement_period = line.split("Periods")[1].strip()
                    if "Reģ. Nr." in statement_period:
                        statement_period = statement_period.split("Reģ. Nr.")[0].strip()
                    break

            bank_info = {
                "bank_name": "AS Swedbank",
                "bank_address": "Balasta dambis 15, Rīga",
                "bank_bic": "HABALV22",
                "bank_reg_no": "40003074764"
            }

            for page in pdf.pages:
                lines = page.extract_text().split("\n")
                
                for line in lines:
                    if "Sākuma atlikums" in line:
                        match = re.search(r"Sākuma atlikums\s+\d{2}\.\d{2}\.\d{4}\s+(\d+\.\d{2})", line)
                        if match:
                            initial_balance = match.group(1)
                    elif "Beigu atlikums" in line:
                        match = re.search(r"Beigu atlikums\s+\d{2}\.\d{2}\.\d{4}\s+(\d+\.\d{2})", line)
                        if match:
                            closing_balance = match.group(1)
                
                for line in lines:
                    transaction_match = re.match(r"^(\d+)\s(\d{2}\.\d{2}\.\d{4})", line)
                    if transaction_match:
                        parts = line.split()
                        trans_id = f"{transaction_id:03}"
                        date = parts[1]
                        beneficiary = ' '.join(parts[2:4])
                        details = ' '.join(parts[4:6])
                        amount_str = parts[-2]

                        amount = re.sub(r"[+-]", "", amount_str)
                        
                        balance = parts[-1] if re.match(r"^\d+\.\d{2}$", parts[-1]) else ""
                        cdt_dbt_ind = "CRDT" if "+" in amount_str else "DBIT"
                        
                        transactions.append({
                            "transaction_id": trans_id,
                            "date": date,
                            "beneficiary": beneficiary,
                            "details": details,
                            "amount": amount,
                            "balance": balance,
                            "cdt_dbt_ind": cdt_dbt_ind
                        })
                        transaction_id += 1

            data = {
                "account_holder": account_holder,
                "account_holder_id": account_holder_id,
                "account_holder_address": account_holder_address,
                "account_number": account_number,
                "statement_period": statement_period,
                "bank_name": bank_info["bank_name"],
                "bank_address": bank_info["bank_address"],
                "bank_bic": bank_info["bank_bic"],
                "bank_reg_no": bank_info["bank_reg_no"],
                "transactions": transactions,
                "initial_balance": initial_balance,
                "closing_balance": closing_balance
            }

            return data

    except Exception:
        return None

if __name__ == "__main__":
    from common_script import process_files
    process_files(extract_pdf_data)
