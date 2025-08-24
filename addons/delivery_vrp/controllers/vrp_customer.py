from odoo import http  
from odoo.http import request  
  
class VrpCustomerController(http.Controller):  
  
    @http.route("/vrp_customer/map_address", type="json", auth="user", methods=["POST"])  
    def map_address_to_customer(self, address):  
        country = request.env["res.country"].sudo().search([("code", "=", str(address.get("country_code")).upper())], limit=1)  
        state = (  
            request.env["res.country.state"]  
            .sudo()  
            .search([("name", "=", address.get("state")), ("country_id", "=", country.id)], limit=1)  
        )  
  
        result = {  
            "street": address.get("street", ""),  
            "city": address.get("city", ""),  
            "zip_code": address.get("zip", ""),  
            "country_id": country.id if country else False,  
            "state_id": state.id if state else False,  
        }  
        return result