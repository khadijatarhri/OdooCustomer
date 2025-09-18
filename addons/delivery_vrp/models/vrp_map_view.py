"""delivery_vrp/models/vrp_map_view.py"""


# models/vrp_map_view.py
from odoo import models, fields, api
import json
import logging

_logger = logging.getLogger(__name__)

class VRPMapView(models.TransientModel):
    _name = 'vrp.map.view'
    _description = 'VRP Map Viewer'

    vehicles_data = fields.Text('Vehicles Data', help="Données JSON des véhicules et itinéraires")

    @api.model
    def default_get(self, fields_list):
        """Récupérer les données par défaut depuis le contexte"""
        result = super().default_get(fields_list)
        vehicles_data = self.env.context.get('default_vehicles_data', [])
        
        # S'assurer que les données sont au format JSON
        if isinstance(vehicles_data, list):
            result['vehicles_data'] = json.dumps(vehicles_data)
        else:
            result['vehicles_data'] = vehicles_data
            
        _logger.info(f"VRP Map View created with {len(vehicles_data) if isinstance(vehicles_data, list) else 'unknown'} vehicles")
        return result
    

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