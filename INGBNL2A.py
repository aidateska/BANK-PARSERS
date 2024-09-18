import pdfplumber
import re

# -------------------- FUNCTION FOR EXTRACTING ACCOUNT INFO --------------------
def extract_account_info_from_pdf(pdf_path):
    account_info = {}
    
    try:
        with pdfplumber.open(pdf_path) as pdf:
            first_page = pdf.pages[0]
            lines = first_page.extract_text().splitlines()

           
            if "Statement Zakelijke rekening" not in lines[0]:
                return None

            for i, line in enumerate(lines):
                if line.strip() == "Period":
                    holder_line = lines[i + 1].strip()
                    account_holder = re.split(r'\d{2}/\d{2}/\d{4}', holder_line)[0].strip()
                    account_info['Account Holder'] = account_holder
                    
                    statement_period_line = lines[i + 1].strip()
                    match = re.search(r'(\d{2}/\d{2}/\d{4}) till (\d{2}/\d{2}/\d{4})', statement_period_line)
                    if match:
                        account_info['Statement Period'] = f"{match.group(1)}-{match.group(2)}"
                        account_info['Statement Date'] = match.group(2)

                if line.strip() == "Accountnumber":
                    account_info['Account Number'] = lines[i + 2].strip()

                if "Opening balance (EUR)" in line:
                    next_line_index = lines.index(line) + 1
                    initial_balance_line = lines[next_line_index].strip()
                    account_info['Initial Balance'] = initial_balance_line.split()[0].strip()

                if "Closing balance (EUR)" in line:
                    next_line_index = lines.index(line) + 1
                    closing_balance_line = lines[next_line_index].strip()
                    account_info['Closing Balance'] = closing_balance_line.split()[0].strip()

            account_info['Bank Name'] = 'ING'
            account_info['Bank Address'] = 'Amsterdam, Bijlmerdreef 106'
            account_info['Bank Registration No.'] = 'FC010062'
            account_info['Bank BIC'] = 'INGBNL2A'
            
    except Exception:
        
        return None

    return account_info

# -------------------- FUNCTION FOR EXTRACTING TRANSACTIONS --------------------
def extract_transactions_from_pdf(pdf_path):
    transactions = []
    transaction_id = 1

    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                if text is None:
                    continue

                lines = text.splitlines()

                current_details = []
                collecting_details = False

                for i, line in enumerate(lines):
                    if line[:10].count('/') == 2 and line[2] == '/' and line[5] == '/':
                        if collecting_details:
                            transactions[-1]["details"] = "\n".join(current_details).strip()
                            current_details = []

                        if '+' in line:
                            sign = '+'
                        elif '-' in line:
                            sign = '-'
                        else:
                            sign = None

                        if sign:
                            date_part = line[:10]
                            rest_part = line[11:].strip()
                            sign_index = rest_part.rfind(sign)
                            amount = rest_part[sign_index+1:].strip()
                            beneficiary = rest_part[:sign_index].strip()

                            cdt_dbt_ind = "CRDT" if sign == '+' else "DBIT"

                            transactions.append({
                                "transaction_id": f"{transaction_id:03}",
                                "date": date_part,
                                "beneficiary": beneficiary,
                                "details": "",
                                "amount": amount.replace(',', ''),
                                "balance": "",
                                "cdt_dbt_ind": cdt_dbt_ind
                            })

                            transaction_id += 1
                            collecting_details = True

                    elif collecting_details:
                        if "Value date" in line:
                            collecting_details = False
                            transactions[-1]["details"] = "\n".join(current_details).strip()
                            current_details = []
                        else:
                            current_details.append(line.strip())

                if collecting_details and current_details:
                    transactions[-1]["details"] = "\n".join(current_details).strip()

    except Exception:
        
        return []

    return transactions

# -------------------- MAIN FUNCTION FOR EXTRACTING PDF DATA --------------------
def extract_pdf_data(pdf_file):
    try:
        account_info = extract_account_info_from_pdf(pdf_file)
        if account_info is None:
            return None

        transactions = extract_transactions_from_pdf(pdf_file)

        data = {
            "account_holder": account_info.get('Account Holder', ''),
            "account_holder_id": "",  
            "account_holder_address": "",  
            "account_number": account_info.get('Account Number', ''),
            "statement_period": account_info.get('Statement Period', ''),
            "bank_name": account_info.get('Bank Name', 'ING'),
            "bank_address": account_info.get('Bank Address', 'Amsterdam, Bijlmerdreef 106'),
            "bank_reg_no": account_info.get('Bank Registration No.', 'FC010062'),
            "bank_vat_code": "",
            "bank_registration_date": "",
            "bank_bic": account_info.get('Bank BIC', 'INGBNL2A'),
            "transactions": transactions,
            "initial_balance": account_info.get('Initial Balance', ''),
            "closing_balance": account_info.get('Closing Balance', '')
        }

        return data

    except Exception:
        
        return None

# -------------------- SCRIPT EXECUTION --------------------
if __name__ == "__main__":
    from common_script import process_files
    process_files(extract_pdf_data)
