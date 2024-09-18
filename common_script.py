import os
import shutil
import json
import xml.etree.ElementTree as ET
from datetime import datetime
from xml.etree.ElementTree import Element, SubElement, ElementTree

# -------------------- FUNCTION FOR INDENTATION --------------------
def indent(elem, level=0):
    i = "\n" + level * "  "
    if len(elem):
        if not elem.text or not elem.text.strip():
            elem.text = i + "  "
        if not elem.tail or not elem.tail.strip():
            elem.tail = i
        for subelem in elem:
            indent(subelem, level + 1)
        if not elem.tail or not elem.tail.strip():
            elem.tail = i
# -------------------- FUNCTION FOR INDENTATION --------------------

# -------------------- FUNCTION FOR CREATING XML --------------------
def create_xml(data, xml_path):
    try:
        if "statement_period" in data and data["statement_period"]:
            try:
                from_datetime = data["statement_period"].split(" - ")[0]
                to_datetime = data["statement_period"].split(" - ")[1]
            except (ValueError, IndexError):
                from_datetime = ""
                to_datetime = ""
        else:
            from_datetime = ""
            to_datetime = ""

        # Set other required values
        required_keys = {
            "creation_datetime": datetime.now().isoformat().split('.')[0],
            "from_datetime": from_datetime,
            "to_datetime": to_datetime,
            "iban": data.get("account_number", ""),
            "account_holder_name": data.get("account_holder", ""),
            "start_date": from_datetime
        }

        for key, default in required_keys.items():
            if key not in data or not data[key]:
                data[key] = default

        statement_date_str = data["start_date"]
        message_id = f"{statement_date_str}-001"
        data["message_id"] = message_id
        data["statement_id"] = message_id

        root = Element("Document", xmlns="urn:iso:std:iso:20022:tech:xsd:camt.053.001.02",
                       xmlns_xsi="http://www.w3.org/2001/XMLSchema-instance",
                       xsi_schemaLocation="urn:iso:std:iso:20022:tech:xsd:camt.053.001.02 camt.053.001.02.xsd")

        bk_to_cstmr_stmt = SubElement(root, "BkToCstmrStmt")
        grp_hdr = SubElement(bk_to_cstmr_stmt, "GrpHdr")
        msg_id = SubElement(grp_hdr, "MsgId")
        msg_id.text = data["message_id"]

        cre_dt_tm = SubElement(grp_hdr, "CreDtTm")
        cre_dt_tm.text = data["creation_datetime"]

        stmt = SubElement(bk_to_cstmr_stmt, "Stmt")
        stmt_id = SubElement(stmt, "Id")
        stmt_id.text = data["statement_id"]

        elctrnc_seq_nb = SubElement(stmt, "ElctrncSeqNb")
        elctrnc_seq_nb.text = "1"

        fr_dt_tm = SubElement(stmt, "FrDtTm")
        fr_dt_tm.text = data["from_datetime"]

        to_dt_tm = SubElement(stmt, "ToDtTm")
        to_dt_tm.text = data["to_datetime"]

        acct = SubElement(stmt, "Acct")
        acct_id = SubElement(acct, "Id")
        iban = SubElement(acct_id, "IBAN")
        iban.text = data["iban"]

        ownr = SubElement(acct, "Ownr")
        nm = SubElement(ownr, "Nm")
        nm.text = data["account_holder"]

        bal = SubElement(stmt, "Bal")
        tp = SubElement(bal, "Tp")
        cd_or_prtry = SubElement(tp, "CdOrPrtry")
        cd = SubElement(cd_or_prtry, "Cd")
        cd.text = "OPBD"

        amt = SubElement(bal, "Amt", Ccy="EUR")
        amt.text = data["initial_balance"]

        dt = SubElement(bal, "Dt")
        dt_txt = SubElement(dt, "Dt")
        dt_txt.text = data["from_datetime"]

        if data["transactions"]:
            txs = SubElement(stmt, "Ntry")
            for transaction in data["transactions"]:
                ntry = SubElement(txs, "Ntry")
                amt = SubElement(ntry, "Amt", Ccy="EUR")
                amt.text = transaction["amount"]
                cdt_dbt_ind = SubElement(ntry, "CdtDbtInd")
                cdt_dbt_ind.text = transaction["cdt_dbt_ind"]

                ntry_dtls = SubElement(ntry, "NtryDtls")
                tx_dtls = SubElement(ntry_dtls, "TxDtls")
                refs = SubElement(tx_dtls, "Refs")
                instr_id = SubElement(refs, "InstrId")
                instr_id.text = transaction["transaction_id"]

                amt_dtls = SubElement(tx_dtls, "AmtDtls")
                amt_instd_amt = SubElement(amt_dtls, "AmtInstdAmt", Ccy="EUR")
                amt_instd_amt.text = transaction["amount"]

                rltd_pties = SubElement(tx_dtls, "RltdPties")
                dbtr = SubElement(rltd_pties, "Dbtr")
                nm = SubElement(dbtr, "Nm")
                nm.text = transaction["beneficiary"]

                rltd_agts = SubElement(tx_dtls, "RltdAgts")
                dbtr_agt = SubElement(rltd_agts, "DbtrAgt")
                fin_instn_id = SubElement(dbtr_agt, "FinInstnId")
                bic = SubElement(fin_instn_id, "BIC")
                bic.text = data["bank_bic"]

                addtl_ntry_inf = SubElement(ntry, "AddtlNtryInf")
                addtl_ntry_inf.text = transaction["details"]

        indent(root)
        tree = ElementTree(root)
        tree.write(xml_path, encoding="utf-8", xml_declaration=True)

    except Exception as e:
        print(f"An error occurred while creating XML: {str(e)}")
# -------------------- FUNCTION FOR CREATING XML --------------------

# -------------------- FUNCTION FOR CREATING JSON --------------------
def create_json(data, json_path):
    output = {
        "output": {
            "document": {
                "statement": {
                    "creation_date_time": data.get("creation_datetime", ""),
                    "from_date_time": data.get("from_datetime", ""),
                    "to_date_time": data.get("to_datetime", ""),
                    "account": {
                        "identifier": {
                            "iban": data.get("account_number", ""),
                            "swift": data.get("bank_bic", ""),
                            "bank": data.get("bank_name", "")
                        },
                        "owner": {
                            "name": data.get("account_holder", ""),
                            "customer_code": data.get("account_holder_id", "")
                        }
                    },
                    "balance": {
                        "opening_balance": {
                            "currency": "EUR",
                            "value": data.get("initial_balance", ""),
                            "type": "OPBD"
                        },
                        "closing_balance": {
                            "currency": "EUR",
                            "value": "",  # Ako imate podatke za zatvaranje, dodajte ih ovde
                            "type": "CLBD"
                        }
                    },
                    "transactions": [
                        {
                            "date": tx["date"],
                            "name": tx["beneficiary"],
                            "reference": tx["transaction_id"],
                            "amount": {
                                "currency": "EUR",
                                "value": tx["amount"]
                            },
                            "type": tx["cdt_dbt_ind"],
                            "description": tx["details"]
                        }
                        for tx in data.get("transactions", [])
                    ]
                }
            }
        }
    }

    with open(json_path, 'w', encoding='utf-8') as json_file:
        json.dump(output, json_file, ensure_ascii=False, indent=4)
# -------------------- FUNCTION FOR CREATING JSON --------------------

# -------------------- MAIN FUNCTION --------------------
def process_files(extract_pdf_data_func):
    import os
    import shutil

    script_dir = os.path.dirname(os.path.abspath(__file__))  # Directory where the script is located
    pdf_folder = os.path.join(script_dir, "PDFs_Pending")  # Folder with PDF files
    xml_folder = os.path.join(script_dir, "XML")  # Folder for XML files
    json_folder = os.path.join(script_dir, "JSON")  # Folder for JSON files
    parsed_folder = os.path.join(script_dir, "PDFs_Parsed")  # Folder for processed PDF files

    if not os.path.exists(pdf_folder):
        print(f"Error: Folder '{pdf_folder}' does not exist.")
        return

    if not os.path.exists(parsed_folder):
        os.makedirs(parsed_folder)

    if os.path.exists(xml_folder):
        shutil.rmtree(xml_folder)
    if os.path.exists(json_folder):
        shutil.rmtree(json_folder)

    os.makedirs(xml_folder, exist_ok=True)
    os.makedirs(json_folder, exist_ok=True)

    pdf_files = [f for f in os.listdir(pdf_folder) if f.endswith(".pdf")]

    for pdf_file in pdf_files:
        pdf_path = os.path.join(pdf_folder, pdf_file)
        try:
            data = extract_pdf_data_func(pdf_path)

            if data:
                xml_filename = os.path.splitext(pdf_file)[0] + '.xml'
                xml_path = os.path.join(xml_folder, xml_filename)
                create_xml(data, xml_path)

                json_filename = os.path.splitext(pdf_file)[0] + '.json'
                json_path = os.path.join(json_folder, json_filename)
                create_json(data, json_path)

                parsed_pdf_path = os.path.join(parsed_folder, pdf_file)
                shutil.move(pdf_path, parsed_pdf_path)

                print(f"Processed file: {pdf_file}")
        except Exception:
            pass  

# -------------------- MAIN FUNCTION --------------------
