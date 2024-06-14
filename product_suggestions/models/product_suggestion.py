import base64
import io

import numpy as np
import numpy.ma as ma
import tensorflow as tf
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import MinMaxScaler, StandardScaler
from tensorflow import keras
from tensorflow.keras.models import load_model

from odoo import api, fields, models


class ProductSuggestion(models.Model):
    _name = "product.suggestion"
    _description = "Product Suggestions"

    user_id = fields.Many2one("res.partner", string="User")
    product_id = fields.Many2one("product.product", string="Product")
    model_data = fields.Binary(string="Model Data")

    @api.model
    def _create_and_save_model(self):
        num_outputs = 32
        num_user_features = 10  # Reemplazar con el número real de features de usuario
        num_item_features = 10  # Reemplazar con el número real de features de producto

        # Definir las arquitecturas de las redes neuronales
        user_NN = tf.keras.models.Sequential(
            [
                tf.keras.layers.Dense(256, activation="relu"),
                tf.keras.layers.Dense(128, activation="relu"),
                tf.keras.layers.Dense(num_outputs, activation="linear"),
            ]
        )

        item_NN = tf.keras.models.Sequential(
            [
                tf.keras.layers.Dense(256, activation="relu"),
                tf.keras.layers.Dense(128, activation="relu"),
                tf.keras.layers.Dense(num_outputs, activation="linear"),
            ]
        )

        # Crear el input y las redes neuronales
        input_user = tf.keras.layers.Input(shape=(num_user_features,))
        vu = user_NN(input_user)
        vu = tf.linalg.l2_normalize(vu, axis=1)

        input_item = tf.keras.layers.Input(shape=(num_item_features,))
        vm = item_NN(input_item)
        vm = tf.linalg.l2_normalize(vm, axis=1)

        # Producto punto entre los dos vectores vu y vm
        output = tf.keras.layers.Dot(axes=1)([vu, vm])

        # Especificar los inputs y el output del modelo
        model = tf.keras.Model([input_user, input_item], output)

        # Compilar el modelo
        tf.random.set_seed(1)
        cost_fn = tf.keras.losses.MeanSquaredError()
        opt = keras.optimizers.Adam(learning_rate=0.01)
        model.compile(optimizer=opt, loss=cost_fn)

        # Guardar el modelo en un buffer
        model_io = io.BytesIO()
        model.save(model_io, save_format="h5")
        model_io.seek(0)
        model_binary = base64.b64encode(model_io.read())

        # Crear o actualizar el registro del modelo
        self.env["product.suggestion"].create({"model_data": model_binary})

    @api.model
    def _load_model(self):
        # Buscar el registro del modelo guardado
        model_record = self.search([], limit=1, order="id desc")
        if not model_record:
            raise ValueError("No model found")

        # Cargar el modelo desde los datos binarios
        model_binary = base64.b64decode(model_record.model_data)
        model_io = io.BytesIO(model_binary)
        model = load_model(model_io)

        return model

    @api.model
    def load_data(self):
        # Obtener todas las categorías de productos
        categories = self.env["product.category"].search([])
        category_ids = categories.ids

        # Obtener datos de res.partner
        partners = self.env["res.partner"].search([])
        user_features_list = []

        # Construir diccionario de productos comprados por cada usuario
        user_purchased_products = {}
        for partner in partners:
            user_features = [partner.sales_frequency, partner.average_purchase_amount]
            product_types = partner.purchased_product_types.ids
            user_features.extend([1 if category in product_types else 0 for category in category_ids])
            user_features_list.append(user_features)
            user_purchased_products[partner.id] = set(
                self.env["account.move.line"]
                .search(
                    [
                        ("move_id.partner_id", "=", partner.id),
                        ("move_id.move_type", "=", "out_invoice"),
                        ("move_id.payment_state", "in", ["in_payment", "paid", "partial"]),
                    ]
                )
                .mapped("product_id.id")
            )

        # Obtener datos de product.product
        products = self.env["product.product"].search([])
        product_features_list = []
        product_dict = {}
        for product in products:
            product_features = [
                product.min_price,
                product.max_price,
                product.average_price,
                product.sales_count,
                product.average_discount,
            ]
            product_features.extend([1 if category.id == product.categ_id.id else 0 for category in categories])
            product_features_list.append(product_features)
            product_dict[product.id] = product_features

        user_features_array = np.array(user_features_list)
        product_features_array = np.array(product_features_list)

        # Construir y_train basado en compras históricas
        y_train = []
        for partner in partners:
            for product in products:
                if product.id in user_purchased_products[partner.id]:
                    y_train.append(1)
                else:
                    y_train.append(0)

        return (
            user_features_array,
            product_features_array,
            np.array(y_train),
            user_features_array.shape[1],
            product_features_array.shape[1],
            products.mapped("id"),
            product_dict,
        )

    @api.model
    def train(self):
        # Cargar el modelo
        model = self._load_model()

        # Cargar los datos
        x_user, x_product, y_train, num_user_features, num_item_features, item_vecs, product_dict = self.load_data()

        # Escalar los datos de entrenamiento
        scalerItem = StandardScaler()
        scalerItem.fit(x_product)
        x_product = scalerItem.transform(x_product)

        scalerUser = StandardScaler()
        scalerUser.fit(x_user)
        x_user = scalerUser.transform(x_user)

        scalerTarget = MinMaxScaler((-1, 1))
        scalerTarget.fit(y_train.reshape(-1, 1))
        y_train = scalerTarget.transform(y_train.reshape(-1, 1))

        # Separar los datos en entrenamiento y prueba
        x_product_train, x_product_test = train_test_split(x_product, train_size=0.80, shuffle=True, random_state=1)
        x_user_train, x_user_test = train_test_split(x_user, train_size=0.80, shuffle=True, random_state=1)
        y_train, y_test = train_test_split(y_train, train_size=0.80, shuffle=True, random_state=1)

        # Definir u_s y i_s
        u_s = 0
        i_s = 0

        # Entrenar el modelo
        tf.random.set_seed(1)
        model.fit([x_user_train[:, u_s:], x_product_train[:, i_s:]], y_train, epochs=30)

        # Evaluar el modelo
        evaluation = model.evaluate([x_user_test[:, u_s:], x_product_test[:, i_s:]], y_test)
        print(f"Model Evaluation: {evaluation}")

        # Guardar el modelo entrenado
        model_io = io.BytesIO()
        model.save(model_io, save_format="h5")
        model_io.seek(0)
        model_binary = base64.b64encode(model_io.read())

        # Actualizar el registro del modelo
        model_record = self.search([], limit=1, order="id desc")
        model_record.write({"model_data": model_binary})

        # Guardar la evaluación del modelo en un archivo o campo si es necesario
        self.env["ir.config_parameter"].sudo().set_param("product_suggestion.model_evaluation", str(evaluation))

    @api.model
    def recommend_products(self, user_id, count=50):
        # Cargar el modelo
        model = self._load_model()

        # Preparar los datos de entrada
        user_features_array, product_features_array, item_vecs, product_dict = self.load_data()

        # Escalar los datos de producto
        scalerItem = StandardScaler()
        scalerItem.fit(product_features_array)
        scaled_item_vecs = scalerItem.transform(product_features_array)

        # Extraer las características del producto usando el modelo entrenado
        input_item_m = tf.keras.layers.Input(shape=(scaled_item_vecs.shape[1],))
        item_NN = model.layers[1]  # Obtener la capa de la red de productos
        vm_m = item_NN(input_item_m)
        vm_m = tf.linalg.l2_normalize(vm_m, axis=1)
        model_m = tf.keras.Model(input_item_m, vm_m)
        vms = model_m.predict(scaled_item_vecs)

        # Calcular las distancias cuadradas
        dim = len(vms)
        dist = np.zeros((dim, dim))
        for i in range(dim):
            for j in range(dim):
                dist[i, j] = np.sum(np.square(vms[i, :] - vms[j, :]))

        # Enmascarar la diagonal
        m_dist = ma.masked_array(dist, mask=np.identity(dist.shape[0]))

        # Obtener las recomendaciones
        recommendations = []
        for i in range(dim):
            min_idx = np.argmin(m_dist[i])
            recommendations.append((item_vecs[i], item_vecs[min_idx]))

        # Guardar las recomendaciones para el usuario
        self.env["res.partner"].browse(user_id)
        for rec in recommendations[:count]:
            product_id = int(rec[1])
            self.env["product.suggestion"].create({"user_id": user_id, "product_id": product_id})

        return recommendations
