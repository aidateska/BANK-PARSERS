import pdfplumber
import re

# -------------------- FUNCTION FOR EXTRACTING PDF DATA --------------------
def extract_text_from_pdf(pdf_path):
    text = ''
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            text += page.extract_text() + '\n'
    return text

def extract_tables_from_pdf(pdf_path):
    tables = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            tables.extend(page.extract_tables())
    return tables

def extract_pdf_info_and_transactions(pdf_path):
    additional_info = {
        "account_holder": "",
        "account_holder_id": "",
        "account_holder_address": "",
        "account_number": "",
        "statement_period": "",
        "statement_date": "",
        "bank_name": "ABN AMRO",
        "bank_address": "Gustav Mahlerlaan 10, 1082 PP",
        "bank_reg_no": "",
        "bank_vat_code": "NL820646660B01",
        "bank_registration_date": "",
        "bank_bic": "ABNANL2A",
        "initial_balance": "",
        "closing_balance": ""
    }
    
    transactions = []
    transaction_id = 1

    try:
        with pdfplumber.open(pdf_path) as pdf:
            
            page = pdf.pages[0]
            text = page.extract_text()

            
            if "Bij- en afschrijvingen" not in text:
                return None

            lines = text.splitlines()

            
            for i, line in enumerate(lines):
                if "Rekeninghouder" in line:
                    additional_info["account_holder"] = line.replace("Rekeninghouder", "").strip()
                    if i + 1 < len(lines):
                        additional_info["account_holder_address"] = lines[i + 1].strip()
                    if i + 2 < len(lines):
                        additional_info["account_holder_address"] += " " + lines[i + 2].strip()

                if "Ondernemersrekenin" in line:
                    additional_info["account_holder_id"] = line.replace("Ondernemersrekenin", "").strip()

                if "Periode" in line:
                    period = line.replace("Periode", "").strip()
                    if "Aantal afschrijvingen" in period:
                        period = period.split("Aantal afschrijvingen")[0].strip()
                    additional_info["statement_period"] = period.replace("t/m", "-")

                    # Extract statement date
                    period_dates = re.findall(r'\d{2}-\d{2}-\d{4}', period)
                    if len(period_dates) == 2:
                        additional_info["statement_date"] = period_dates[1]

            # Extract initial and closing balances
            initial_balance_match = re.search(r'Saldo\s+\d{2}-\d{2}-\d{4}\s+€\s+([\d\.,]+)', text)
            closing_balance_match = re.search(r'Saldo\s+\d{2}-\d{2}-\d{4}.*?Saldo\s+\d{2}-\d{2}-\d{4}\s+€\s+([\d\.,]+)', text, re.S)

            if initial_balance_match:
                additional_info["initial_balance"] = initial_balance_match.group(1).replace(".", "").replace(",", ".")

            if closing_balance_match:
                additional_info["closing_balance"] = closing_balance_match.group(1).replace(".", "").replace(",", ".")

            # Extract transactions
            for page in pdf.pages:
                text = page.extract_text()
                lines = text.splitlines()

                current_details = []
                collecting_details = False

                for line in lines:
                    columns = line.split()

                    if len(columns) >= 2 and len(columns[0]) == 10 and columns[0][2] == '-' and columns[0][5] == '-':
                        if collecting_details and current_details:
                            transactions[-1]["details"] = "\n".join(current_details).strip()
                            current_details = []

                        date = columns[0]
                        last_column = columns[-1]
                        if len(last_column) > 2 and last_column[-3] == ',' and last_column[-2:].isdigit():
                            amount = last_column
                            beneficiary = " ".join(columns[1:-1])

                            transactions.append({
                                "transaction_id": f"{transaction_id:03}",
                                "date": date,
                                "beneficiary": beneficiary.strip(),
                                "details": "",
                                "amount": amount,
                                "balance": "",
                                "cdt_dbt_ind": "CRDT" if len(columns) == 3 else "DBIT"
                            })
                            transaction_id += 1
                            collecting_details = True

                    elif collecting_details:
                        if "Aantal afschrijvingen" in line:
                            collecting_details = False
                        else:
                            current_details.append(line.strip())

                if collecting_details and current_details:
                    transactions[-1]["details"] = "\n".join(current_details).strip()

        
        result = {
            **additional_info,
            "transactions": transactions
        }

        return result

    except Exception:
        # Skip the file and return None if there is an error
        return None

# -------------------- FUNCTION FOR PROCESSING FILES --------------------
if __name__ == "__main__":
    from common_script import process_files
    process_files(extract_pdf_info_and_transactions)
