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

def parse_pdf_text(text, tables):
    lines = text.split('\n')
    header = {}
    transactions = []
    closing_balance = {}
    statement_period = {}

    # Find line containing "Opening balance" and extract currency and balance
    for line in lines:
        match = re.search(r'([A-Z]{3}) Opening balance (\d{4}-\d{2}-\d{2}) (\d+\.\d+)', line)
        if match:
            header['currency'] = match.group(1)
            header['balance'] = match.group(3)
            header['statement_date'] = match.group(2)
            break

    # Find line containing "Closing balance" and extract currency and balance
    for line in lines:
        match = re.search(r'([A-Z]{3}) Closing balance (\d{4}-\d{2}-\d{2}) (\d+\.\d+)', line)
        if match:
            closing_balance['currency'] = match.group(1)
            closing_balance['balance'] = match.group(3)
            closing_balance['statement_date'] = match.group(2)
            break

    # Extract statement period from the text
    for line in lines:
        match = re.search(r'Period (\d{4}-\d{2}-\d{2}) - (\d{4}-\d{2}-\d{2})', line)
        if match:
            statement_period['from_date'] = match.group(1) + 'T00:00:01'  # Set time to 00:00:01
            statement_period['to_date'] = match.group(2) + 'T23:59:59'    # Set time to 23:59:59
            break

    # Parse other information from text and tables
    header.update({
        "account_holder": lines[1].strip().split('„')[0].strip() if len(lines) > 1 else "",
        "account_holder_id": lines[2].strip().split('ID No ')[1].split()[0] if len(lines) > 2 else "",
        "account_holder_address": " ".join(lines[3].strip().split('Reg.no ')[0].split(',')[0:-1]) if len(lines) > 3 else "",
        "account_number": lines[4].strip().split('Account ')[1].strip().split(' Bank')[0] if len(lines) > 4 else "",
        "statement_period": " ".join(lines[5].strip().split('Period ')[1].split()[:3]) if len(lines) > 5 else "",
        "bank_name": lines[1].strip().split('„')[1].split('”')[0] if '„' in lines[1] and '”' in lines[1] else "",
        "bank_address": " ".join(lines[2].strip().split('ID No ')[1].split(' ')[1:]) if len(lines) > 2 else "",
        "bank_reg_no": lines[3].strip().split('Reg.no ')[1].split(',')[0] if len(lines) > 3 and 'Reg.no' in lines[3] else "",
        "bank_vat_code": lines[3].strip().split('VAT payer code ')[1] if len(lines) > 3 and 'VAT payer code' in lines[3] else "",
        "bank_registration_date": lines[5].strip().split()[-1] if len(lines) > 5 else "",
        "bank_bic": lines[6].strip().split('BIC: ')[1] if len(lines) > 6 and 'BIC:' in lines[6] else "",
    })

    # Extract transactions from tables
    for table in tables:
        for row in table:
            if len(row) > 1 and row[0].isdigit():
                transaction_id = row[0]
                date = row[1]
                beneficiary = " ".join(row[2].split()) if len(row) > 2 else ""
                details = " ".join(row[3].split()) if len(row) > 3 else ""
                amount = row[-2] if len(row) > 4 else ""
                balance = row[-1] if len(row) > 4 else ""

                # Determine debit/credit indicator based on amount sign
                if amount.startswith('-'):
                    amount = amount[1:]  # Remove the minus sign
                    cdt_dbt_ind = 'DBIT'  # Credit indicator for negative amounts
                else:
                    cdt_dbt_ind = 'CRDT'  # Debit indicator for positive amounts

                transactions.append({
                    "transaction_id": transaction_id,
                    "date": date,
                    "beneficiary": beneficiary,
                    "details": details,
                    "amount": amount,
                    "balance": balance,
                    "cdt_dbt_ind": cdt_dbt_ind
                })

    return header, transactions, closing_balance, statement_period

def extract_pdf_data(pdf_file):
    try:
        with pdfplumber.open(pdf_file) as pdf:
            # Brzo provjeri postoji li ključna riječ "HABALT22" u bilo kojoj stranici PDF-a
            if not any("HABALT22" in page.extract_text() for page in pdf.pages):
                return None  # Preskoči PDF ako ključna riječ nije prisutna

            # Nastavi s ekstrakcijom teksta ako je ključna riječ pronađena
            text = ''.join(page.extract_text() for page in pdf.pages)
            tables = extract_tables_from_pdf(pdf_file)
            header, transactions, closing_balance, statement_period = parse_pdf_text(text, tables)

            data = {
                "account_holder": header.get("account_holder", ""),
                "account_holder_id": header.get("account_holder_id", ""),
                "account_holder_address": header.get("account_holder_address", ""),
                "account_number": header.get("account_number", ""),
                "statement_period": statement_period.get("from_date", "") + " - " + statement_period.get("to_date", ""),
                "bank_name": header.get("bank_name", ""),
                "bank_address": header.get("bank_address", ""),
                "bank_reg_no": header.get("bank_reg_no", ""),
                "bank_vat_code": header.get("bank_vat_code", ""),
                "bank_registration_date": header.get("bank_registration_date", ""),
                "bank_bic": header.get("bank_bic", ""),
                "transactions": transactions,
                "initial_balance": header.get("balance", "")
            }

            return data

    except Exception:
        return None  


# -------------------- FUNCTION FOR EXTRACTING PDF DATA --------------------

# Automatically trigger processing when this script is run directly
if __name__ == "__main__":
    from common_script import process_files
    process_files(extract_pdf_data)
