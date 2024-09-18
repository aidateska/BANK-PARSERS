import pdfplumber
import re

# -------------------- FUNCTION FOR EXTRACTING PDF DATA --------------------
def extract_info_from_pdf(pdf_path):
    info = {}
    transactions = []
    transaction_id = 1

    with pdfplumber.open(pdf_path) as pdf:
        first_page = pdf.pages[0]
        text = first_page.extract_text()

        
        if "Norēķinu konts EUR" not in text:
            return None  

        
        date_matches = re.findall(r'(\d{2}\.\d{2}\.\d{4})', text)
        if len(date_matches) >= 2:
            info["statement_period"] = f"{date_matches[0]} - {date_matches[1]}"  

        
        account_holder_match = re.search(r'(.*?)Norēķinu konts EUR', text)
        if account_holder_match:
            info["account_holder"] = account_holder_match.group(1).strip()

        info["account_holder_address"] = ""  

        
        account_number_match = re.search(r'Norēķinu konts EUR\s+(LV\d+.*)', text)
        if account_number_match:
            info["account_number"] = account_number_match.group(1).strip()

        
        period_match = re.search(r'Pārskats par periodu\s+(\d{2}\.\d{2}\.\d{4})\s+-\s+(\d{2}\.\d{2}\.\d{4})', text)
        if period_match:
            info["statement_period"] = f"{period_match.group(1)} - {period_match.group(2)}"

        info["bank_name"] = "AS SEB Banka"
        info["bank_bic"] = "UNLALV2X"
        info["bank_reg_no"] = "40003816496."
        info["bank_address"] = "Gustava Zemgala gatve 73"

        
        closing_balance_match = re.search(r'Beigu atlikums\s+(-?\d+,\d+)', text)
        if closing_balance_match:
            closing_balance = closing_balance_match.group(1).replace('.', ',')
            
            lines = text.split('\n')
            for i, line in enumerate(lines):
                if 'Beigu atlikums' in line:
                    if i > 0:
                        initial_balance_match = re.search(r'(-?\d+,\d+)', lines[i-1])
                        if initial_balance_match:
                            info["initial_balance"] = initial_balance_match.group(1).replace('.', ',')
                    break
        else:
            info["initial_balance"] = ""

        info["closing_balance"] = closing_balance if 'closing_balance' in locals() else ""

        # Extract transactions from all pages
        for page in pdf.pages:
            text = page.extract_text()
            lines = text.split('\n')

            
            header_index = None
            for i, line in enumerate(lines):
                if 'Datums Dok. Maksātājs/Saņēmējs Maksājuma mērķis Summa' in line:
                    header_index = i
                    break

            if header_index is not None:
                for line in lines[header_index + 1:]:  # Skip header line
                    match = re.match(r'(\d{2}\.\d{2}\.\d{4})\s+(.*?)\s+(-?\d+,\d+)', line)
                    
                    if match:
                        date = match.group(1)
                        amount = match.group(3).replace('.', ',')  
                        
                        amount_display = amount.lstrip('-') 
                        rest_of_line = line[len(date):line.rfind(amount)].strip()
                        split_index = find_split_index(rest_of_line)
                        beneficiary = rest_of_line[:split_index].strip()
                        details = rest_of_line[split_index:].strip()
                        cdt_dbt_ind = 'CRDT' if not amount.startswith('-') else 'DBIT'
                        
                        transaction = {
                            "transaction_id": f"{transaction_id:03}",
                            "date": date,
                            "beneficiary": beneficiary,
                            "details": details,
                            "amount": amount_display,  
                            "balance": "",
                            "cdt_dbt_ind": cdt_dbt_ind
                        }
                        transactions.append(transaction)
                        transaction_id += 1

    
    return {
        "statement_period": info.get("statement_period", ""),
        "account_number": info.get("account_number", ""),
        "account_holder": info.get("account_holder", ""),
        "initial_balance": info.get("initial_balance", ""),
        "closing_balance": info.get("closing_balance", ""),
        "bank_name": info.get("bank_name", ""),
        "bank_bic": info.get("bank_bic", ""),
        "bank_reg_no": info.get("bank_reg_no", ""),
        "bank_address": info.get("bank_address", ""),
        "transactions": transactions
    }

def find_split_index(text):
    
    words = text.split()
    
    
    if len(words) < 2:
        return len(text) // 2
    
    
    last_index = 0
    for i in range(1, len(words)):
        if len(words[i]) > 15:  
            return text.find(words[i])  
    
   
    return len(text) // 2

# -------------------- FUNCTION FOR EXTRACTING PDF DATA --------------------

# Automatically trigger processing when this script is run directly
if __name__ == "__main__":
    from common_script import process_files
    process_files(extract_info_from_pdf)
