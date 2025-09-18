# models/vrp_map_view.py - VERSION FINALE CORRIGÉE
import logging
from odoo import models, fields, api
import json

_logger = logging.getLogger(__name__)

class VRPMapView(models.TransientModel):
    _name = 'vrp.map.view'
    _description = 'VRP Map Viewer - FINAL'

    vehicles_data = fields.Text('Vehicles Data', help="Données JSON des véhicules et itinéraires")

    @api.model
    def default_get(self, fields_list):
        """Récupération sécurisée des données par défaut"""
        _logger.info("=== VRP MAP VIEW DEFAULT_GET FINAL ===")
        _logger.info(f"Fields demandés: {fields_list}")
        
        result = super().default_get(fields_list)
        
        # Vérifier si des données sont passées dans le contexte
        context_data = self.env.context.get('default_vehicles_data')
        
        if context_data:
            _logger.info(f"Données context trouvées: {type(context_data)}")
            
            if isinstance(context_data, list):
                # ✅ Toujours sérialiser une liste Python
                result['vehicles_data'] = json.dumps(context_data, ensure_ascii=False)
                _logger.info(f"Liste context sérialisée: {len(context_data)} éléments")
            
            elif isinstance(context_data, str):
                # Vérifier que c'est du JSON valide
                try:
                    parsed = json.loads(context_data)
                    if isinstance(parsed, list):
                        # ✅ On re-dumps pour éviter les chaînes doublement sérialisées
                        result['vehicles_data'] = json.dumps(parsed, ensure_ascii=False)
                        _logger.info("String JSON valide reformatée en liste")
                    else:
                        _logger.error(f"Context string JSON ne contient pas une liste: {type(parsed)}")
                        result['vehicles_data'] = '[]'
                except json.JSONDecodeError:
                    _logger.error("Context string n'est pas du JSON valide")
                    result['vehicles_data'] = '[]'
            
            else:
                _logger.warning(f"Type de données context non supporté: {type(context_data)}")
                result['vehicles_data'] = '[]'
        
        else:
            _logger.info("Aucune donnée context, utilisation par défaut")
            result['vehicles_data'] = '[]'
        
        return result

    @api.model
    def create(self, vals):
        """Surcharge pour validation et debugging"""
        _logger.info(f"=== CRÉATION VRP MAP VIEW FINALE ===")
        vehicles_data_input = vals.get('vehicles_data', '[]')
        _logger.info(f"Type d'entrée: {type(vehicles_data_input)}")
        _logger.info(f"Contenu (100 premiers chars): {str(vehicles_data_input)[:100]}...")
        
        try:
            if isinstance(vehicles_data_input, str):
                # ✅ Tenter de parser la chaîne
                vehicles_data = json.loads(vehicles_data_input)
                if isinstance(vehicles_data, list):
                    vals['vehicles_data'] = json.dumps(vehicles_data, ensure_ascii=False)
                    _logger.info(f"✅ String JSON valide avec {len(vehicles_data)} véhicules")
                else:
                    _logger.error(f"JSON parsé n'est pas une liste: {type(vehicles_data)}")
                    vals['vehicles_data'] = '[]'
            
            elif isinstance(vehicles_data_input, list):
                # ✅ Déjà une liste Python
                vals['vehicles_data'] = json.dumps(vehicles_data_input, ensure_ascii=False)
                _logger.info(f"✅ Liste Python sérialisée avec {len(vehicles_data_input)} véhicules")
            
            else:
                _logger.error(f"Type de données non supporté: {type(vehicles_data_input)}")
                vals['vehicles_data'] = '[]'
                
        except json.JSONDecodeError as e:
            _logger.error(f"❌ Erreur parsing JSON: {e}")
            vals['vehicles_data'] = '[]'
        except Exception as e:
            _logger.error(f"❌ Erreur inattendue: {e}")
            vals['vehicles_data'] = '[]'
        
        # Créer l'enregistrement
        record = super().create(vals)
        
        # Vérification finale
        try:
            final_data = json.loads(record.vehicles_data)
            _logger.info(f"✅ Enregistrement créé - ID: {record.id}")
            _logger.info(f"Données finales: {len(final_data)} véhicules stockés")
            
            # Debug détaillé
            for i, vehicle in enumerate(final_data):
                waypoints_count = len(vehicle.get('waypoints', []))
                _logger.info(f"  Véhicule {i}: {vehicle.get('vehicle_name', 'N/A')} - {waypoints_count} waypoints")
                
        except Exception as e:
            _logger.error(f"❌ Erreur vérification finale: {e}")
        
        return record


    """

## 📝 Explication ligne par ligne

### 1. `from odoo import models, fields, api`

* **`odoo`** : c’est le framework ERP (Enterprise Resource Planning) sur lequel ce module est construit.
* **`models`** : permet de créer des classes qui représentent des modèles de données (équivalent de tables dans une base de données).
* **`fields`** : sert à définir des **champs** (colonnes de la base de données).
  Exemple : `fields.Text('Vehicles Data')` → un champ texte pour stocker des données.
* **`api`** : contient des décorateurs comme `@api.model`, `@api.multi`, `@api.depends` qui définissent le comportement des méthodes.

---

### 2. `import json`

* **`json`** : c’est une librairie Python standard qui permet de **convertir** entre :

  * un objet Python (liste, dictionnaire, etc.)
  * une chaîne de caractères au format JSON (utilisé pour échanger des données entre programmes).

Exemple :

```python
import json
data = {"nom": "Ali", "age": 25}
texte = json.dumps(data)   # Convertit en string JSON
print(texte)   # {"nom": "Ali", "age": 25}
```

---

### 3. `class VRPMapView(models.TransientModel):`

* **`TransientModel`** : modèle temporaire dans Odoo.
  Contrairement à `models.Model` (qui stocke en base de données de manière permanente), `TransientModel` est utilisé pour des données temporaires (souvent dans des assistants/wizards).

---

### 4. `vehicles_data = fields.Text('Vehicles Data')`

* Définition d’un champ `vehicles_data` de type texte.
* `'Vehicles Data'` est juste le **libellé** qui apparaîtra dans l’interface.

---

### 5. `@api.model`

* **Décorateur** qui indique que la méthode ne dépend pas d’un enregistrement particulier.
* En gros, c’est une méthode **de classe** qui agit au niveau global.

---

### 6. `def default_get(self, fields_list):`

* **`default_get`** : méthode spéciale d’Odoo appelée lorsqu’on ouvre un formulaire pour **pré-remplir les champs par défaut**.
* **`fields_list`** : liste des champs à initialiser (envoyée automatiquement par Odoo).

---

### 7. `result = super().default_get(fields_list)`

* **`super()`** : permet d’appeler la version **parente** de la méthode.
  Ici, ça appelle `default_get` défini dans `models.TransientModel`.
* Comme ça, tu gardes le comportement de base d’Odoo, et tu peux ajouter ton propre traitement **par-dessus**.

---

### 8. `vehicles_data = self.env.context.get('default_vehicles_data', [])`

* **`self.env`** : environnement d’exécution dans Odoo, qui contient :

  * `self.env.user` → l’utilisateur connecté
  * `self.env.company` → la société courante
  * `self.env.context` → le contexte courant
* **`context`** : c’est un dictionnaire (clé → valeur) qui transporte des informations temporaires entre les méthodes.
* **`.get('default_vehicles_data', [])`** :

  * `.get(clé, valeur_par_défaut)` → permet de récupérer une valeur depuis le dictionnaire.
  * Ici, on cherche la clé `'default_vehicles_data'`.
  * Si elle n’existe pas, on retourne `[]` (une liste vide).

👉 Ça permet donc de récupérer la liste des véhicules passée par le contexte, ou sinon mettre une liste vide par défaut.

---

### 9. `result['vehicles_data'] = json.dumps(vehicles_data)`

* `json.dumps(objet_python)` → convertit un objet Python (ici une liste `vehicles_data`) en **chaîne JSON**.
* Pourquoi ? Parce que `vehicles_data` est un champ **Texte** dans Odoo, et il ne peut stocker que du texte (string), pas une liste Python directement.

Exemple :

```python
vehicles_data = [{"id": 1, "name": "Camion A"}, {"id": 2, "name": "Camion B"}]
json.dumps(vehicles_data)
# Résultat: '[{"id": 1, "name": "Camion A"}, {"id": 2, "name": "Camion B"}]'
```

"""