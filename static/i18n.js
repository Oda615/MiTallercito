/* MiTallercito · traducción de la interfaz.
 * El código está escrito en español; si el idioma es inglés, esta capa traduce todo lo que se pinta
 * (textos, placeholders, títulos, avisos, confirmaciones y errores del servidor) con un diccionario
 * exacto y unas reglas para frases con números. Para añadir un idioma: otro diccionario + reglas. */
(function () {
  const EN = {
    // --- navegación y general
    'Inicio': 'Home', 'Calculadora': 'Calculator', 'Pedidos': 'Orders', 'Contabilidad': 'Accounting', 'Extracto': 'Report',
    'Impresoras': 'Printers', 'Catálogo': 'Catalog', 'Ajustes': 'Settings', 'Mantenimiento': 'Maintenance', 'salir': 'log out',
    'Hecho con': 'Made with', 'Guardar': 'Save', 'Cancelar': 'Cancel', 'Borrar': 'Delete', 'Añadir': 'Add', 'Crear': 'Create',
    'Quitar': 'Remove', 'Nuevo': 'New', 'Listo': 'Done', 'Sí': 'Yes', 'No': 'No', 'sí': 'yes', 'no': 'no', 'Total': 'Total', '—': '—',
    'Entrar': 'Log in', 'Usuario': 'Username', 'Contraseña': 'Password', 'todos': 'all', 'ok': 'ok', 'Aviso': 'Alert',
    'Nombre': 'Name', 'Tipo': 'Type', 'Color': 'Colour', 'Fecha': 'Date', 'Estado': 'Status', 'Notas': 'Notes', 'Email': 'Email',
    'Teléfono': 'Phone', 'Dirección': 'Address', 'Cantidad': 'Quantity', 'Unidad': 'Unit', 'Activa': 'Active', 'Activo': 'Active',
    'Precio': 'Price', 'Coste': 'Cost', 'Importe': 'Amount', 'Concepto': 'Description', 'Categoría': 'Category', 'Persona': 'Person',
    'Quién': 'Who', 'Qué': 'What', 'Cliente': 'Customer', 'Contacto': 'Contact', 'Canal': 'Channel', 'Origen': 'Source',
    'Producto': 'Product', 'Productos': 'Products', 'Descripción': 'Description', 'Foto': 'Photo', 'Stock': 'Stock', 'Rol': 'Role',
    'Año': 'Year', 'Exportar CSV': 'Export CSV', 'Historial': 'History', 'Archivos': 'Files', 'Movimientos': 'Movements',

    // --- primer arranque
    'Primer arranque': 'First run', 'Configura tu tienda. Todo esto se puede cambiar después en Ajustes.': 'Set up your shop. You can change all of this later in Settings.',
    'Código de instalación': 'Setup code', 'sale al instalar / mitallercito setup-token': 'shown by the installer / mitallercito setup-token',
    'Tu usuario (administrador)': 'Your username (admin)', 'Contraseña (mín. 8)': 'Password (min. 8)', 'Repite la contraseña': 'Repeat password',
    'Nombre de la tienda': 'Shop name', 'Quiénes sois (separados por coma)': 'Who are you (comma separated)', 'Idioma': 'Language',
    'Consumo medio en W (mira la etiqueta o mide con un enchufe medidor; una FDM típica gasta 100-250 W) y lo que te costó, para repartir la amortización.':
      'Average power in W (check the label or use a plug-in meter; a typical FDM printer draws 100-250 W) and what it cost you, to spread its depreciation.',
    'W medios': 'Avg. W', 'Precio €': 'Price €', '+ impresora': '+ printer', 'p.ej. Prusa MK4': 'e.g. Prusa MK4',
    'Marca los que uses y pon el precio que pagas por envase.': 'Tick the ones you use and enter what you pay per spool/bottle.',
    '+ material': '+ material', 'Tipo': 'Type', '€ envase': '€ per spool', 'Precios': 'Pricing', 'Precio de la luz €/kWh': 'Electricity price €/kWh',
    'Margen de beneficio %': 'Profit margin %', 'Tu tiempo €/hora': 'Your time €/hour', 'Aplicar 21%': 'Apply 21%', 'Aplicar 10%': 'Apply 10%',
    'Sin IVA (particular)': 'No VAT (private seller)', 'Crear mi tienda': 'Create my shop', 'Las contraseñas no coinciden': 'Passwords do not match',
    '¡Tienda creada!': 'Shop created!', 'Error': 'Error', 'Resina estándar': 'Standard resin', 'Resina': 'Resin',

    // --- inicio
    'Hola': 'Hi', '+ Nuevo pedido': '+ New order', 'Calcular precio': 'Price a print', 'Apuntar gasto': 'Add expense',
    'cobrado este mes': 'collected this month', 'beneficio este mes': 'profit this month', 'pedidos en marcha': 'orders in progress',
    'pendiente de cobro': 'unpaid', 'pendiente de cobro ·': 'unpaid ·', 'pendiente de cobro · ': 'unpaid · ', 'vs mes pasado': 'vs last month', 'Próximas entregas': 'Upcoming deliveries', 'ver todos': 'see all',
    'Entrega': 'Due', 'sin fecha': 'no date', 'hoy': 'today', 'mañana': 'tomorrow', 'Nada pendiente. 🎉': 'Nothing pending. 🎉',
    'Sin cobrar': 'Unpaid', 'Todo cobrado.': 'All paid.', 'Stock bajo': 'Low stock', 'Stock bajo:': 'Low stock:', 'registrar compra': 'record purchase',
    'Lo más vendido este mes': 'Best sellers this month', 'Aún no hay ventas este mes.': 'No sales yet this month.', 'Uds': 'Qty',
    'Facturado': 'Invoiced', 'Últimos movimientos': 'Latest movements', 'contabilidad': 'accounting', 'Sin movimientos.': 'No movements.',
    'ver stock': 'see stock', 'sin conexión': 'offline',

    // --- calculadora
    'Importar del laminador': 'Import from slicer', 'Arrastra aquí el': 'Drop the', 'o el': 'or the', '.3mf laminado': 'sliced .3mf',
    '(Snapmaker Orca, Anycubic Slicer Next, Orca, Bambu, Prusa, Cura). Rellena tiempo, impresora, gramos por color y coste del laminador. Se lee en tu navegador: el archivo no se sube.':
      '(Snapmaker Orca, Anycubic Slicer Next, Orca, Bambu, Prusa, Cura). Fills in time, printer, grams per colour and slicer cost. Read in your browser: the file is not uploaded.',
    'Impresión': 'Print', 'Impresora': 'Printer', 'Horas': 'Hours', 'Minutos': 'Minutes', 'Piezas que salen': 'Pieces per job',
    'Mete el tiempo real de la impresión (no el del laminador si sabes que se desvía). Si imprimes una placa con varias piezas, pon el total y cuántas salen.':
      'Enter the real print time (not the slicer estimate if you know it is off). For a plate with several pieces, enter the total and how many come out.',
    'Material': 'Material', 'Por gramos / ml': 'By grams / ml', 'Coste del laminador (€)': 'Slicer cost (€)', '+ material / color': '+ material / colour',
    'Coste de material del laminador €': 'Material cost from slicer €', 'ej. 1,84': 'e.g. 1.84', 'g / ml': 'g / ml',
    'Coste total que te da el slicer. En este modo no se suma merma (el laminador ya cuenta purgas y torre). Los gramos de abajo se usan solo para descontar stock y para el extracto.':
      'Total cost reported by the slicer. No waste is added in this mode (the slicer already counts purges and the prime tower). The grams below are only used for stock and reports.',
    'Mano de obra': 'Labour', 'Preparación (min)': 'Preparation (min)', 'Postprocesado (min)': 'Post-processing (min)',
    'Otros gastos': 'Other costs', '+ gasto (embalaje, imanes, pintura…)': '+ cost (packaging, magnets, paint…)', 'Concepto': 'Item', '€': '€',
    'Venta': 'Sale', 'Margen %': 'Margin %', 'Comisión %': 'Fee %', 'Comisión fija €': 'Fixed fee €', 'Redondeo': 'Rounding',
    'Sin redondeo': 'No rounding', 'x,99': 'x.99', 'x,50': 'x.50', '€ entero': 'whole €', 'Precio mínimo € (por pieza)': 'Minimum price € (per piece)',
    'IVA': 'VAT', 'Aplicar IVA': 'Apply VAT', 'Sin IVA': 'No VAT', 'Con IVA': 'With VAT', 'B2C': 'B2C', 'B2B': 'B2B',
    'Por defecto toma los valores de Ajustes; aquí los puedes cambiar solo para este cálculo.': 'Defaults come from Settings; changes here only affect this calculation.',
    'Precio total': 'Total price', 'Calcular': 'Calculate', 'Recalcular': 'Recalculate', 'Vaciar el formulario': 'Clear the form',
    'Rellena los datos y pulsa Calcular.': 'Fill in the details and press Calculate.', 'Has cambiado datos: este precio ya no vale. Pulsa': 'You changed something: this price is out of date. Press',
    'Por pieza:': 'Per piece:', 'sin IVA': 'excl. VAT', 'con IVA': 'incl. VAT', 'sin IVA aplicado': 'no VAT applied',
    'te cuesta (total)': 'your cost (total)', 'ganas (total)': 'you earn (total)', 'IVA a ingresar': 'VAT to pay',
    'Amortización': 'Depreciation', 'Electricidad': 'Electricity', 'Mantenimiento': 'Maintenance', 'Merma': 'Waste', 'Preparación': 'Preparation',
    'Postprocesado': 'Post-processing', 'Riesgo fallo': 'Failure risk', 'Margen': 'Margin', 'Comisión plataforma': 'Marketplace fee',
    'Nombre (ej. Grip AK, llavero…)': 'Name (e.g. phone stand, keychain…)', 'Guardar en catálogo': 'Save to catalog', 'Añadir a pedido': 'Add to order',
    'Se aplica el': 'The', 'precio mínimo': 'minimum price', '. Por eso cambiar el margen no mueve el precio hasta que lo supere. Puedes bajarlo en «Precio mínimo €».':
      '. So changing the margin won’t move the price until it goes above it. You can lower it in “Minimum price €”.',
    'Redondeado desde': 'Rounded from', 'Revisa que cada color apunta al material correcto.': 'Check that each colour points to the right material.',
    'Datos importados: revisa los materiales y pulsa Calcular': 'Imported: check the materials and press Calculate',
    'Mete al menos el tiempo de impresión o el material': 'Enter at least the print time or the material', 'Pulsa Calcular primero': 'Press Calculate first',
    'Ponle nombre': 'Give it a name', 'Guardado en catálogo': 'Saved to catalog', 'Guardado en catálogo con su archivo': 'Saved to catalog with its file',
    'Ficha:': 'Print sheet:', 'Placa': 'Plate', 'coste laminador': 'slicer cost', 'Leyendo': 'Reading',

    // --- pedidos
    'presupuesto': 'quote', 'pendiente': 'pending', 'imprimiendo': 'printing', 'listo': 'ready', 'entregado': 'delivered', 'cancelado': 'cancelled',
    'presupuesto ·': 'quote ·', 'pendiente ·': 'pending ·', 'imprimiendo ·': 'printing ·', 'listo ·': 'ready ·', 'entregado ·': 'delivered ·', 'cancelado ·': 'cancelled ·',
    'Benef.': 'Profit', 'Cobro': 'Payment', 'Lo lleva': 'Assigned to', 'Sin pedidos': 'No orders', 'Nuevo pedido': 'New order',
    'Fecha entrega': 'Due date', 'Dirección de envío': 'Shipping address', 'Interno': 'Internal', 'Tienda online': 'Online store',
    'Líneas': 'Lines', 'Precio ud': 'Unit price', 'Coste ud': 'Unit cost', 'Ficha': 'Sheet', 'Ficha ✓': 'Sheet ✓', 'Ficha de impresión': 'Print sheet',
    '+ línea manual': '+ manual line', '+ desde catálogo…': '+ from catalog…', 'Envío €': 'Shipping €', 'Descuento €': 'Discount €',
    'Beneficio estimado': 'Estimated profit', 'Cobrado': 'Paid', 'Cobró': 'Paid to', 'Fecha cobro': 'Payment date',
    '— STL, 3MF del proyecto laminado, G-code… para poder repetirlo igual': '— STL, sliced 3MF project, G-code… so you can reprint it exactly',
    'Sin archivos todavía.': 'No files yet.', 'se sube al guardar': 'uploads on save', 'colores, medidas, enlace al modelo…': 'colours, sizes, link to the model…',
    'tel, @insta, email…': 'phone, @insta, email…', 'Repetir pedido': 'Repeat order', 'Presupuesto PDF': 'Quote PDF', 'Albarán PDF': 'Delivery note PDF',
    'Enviar a impresora': 'Send to printer', 'Impresiones reales:': 'Actual prints:', 'Pedido guardado': 'Order saved', 'Directo': 'Direct', 'Feria': 'Fair',
    'Altura de capa': 'Layer height', 'Primera capa': 'First layer', 'Relleno': 'Infill', 'Patrón': 'Pattern', 'Perímetros': 'Walls',
    'Capas sup./inf.': 'Top/bottom layers', 'Boquilla': 'Nozzle', 'Soportes': 'Supports', 'Perfil': 'Profile', 'Filamentos': 'Filaments',
    'Materiales': 'Materials', 'Archivo de origen': 'Source file', 'pendiente de pago': 'awaiting payment',
    '¿Borrar pedido?': 'Delete order?', '¿Quitar este archivo del pedido?': 'Remove this file from the order?', '¿Quitar archivo?': 'Remove file?',
    'Este pedido no tiene STL ni 3MF adjunto.': 'This order has no STL or 3MF attached.', 'Si algún día quieres repetirlo igual, te hará falta.': 'You will need it to reprint it exactly some day.',
    '¿Guardar sin archivo?': 'Save without a file?', 'Se creará un pedido nuevo (pendiente) con las mismas piezas, fichas de impresión y archivos. ¿Seguir?':
      'A new (pending) order will be created with the same pieces, print sheets and files. Continue?',
    'Permite ventanas emergentes': 'Allow pop-ups',
    // documentos
    'Presupuesto': 'Quote', 'Albarán': 'Delivery note', 'Válido hasta': 'Valid until', 'Envío': 'Shipping', 'Descuento': 'Discount',
    'Base imponible': 'Subtotal', 'Observaciones': 'Notes', 'borrador': 'draft',

    // --- contabilidad
    'ingresos': 'income', 'gastos': 'expenses', 'beneficio': 'profit', 'pedidos abiertos': 'open orders', 'Backup BD': 'DB backup',
    'Por mes': 'By month', 'Entre vosotros': 'Between partners', 'Ha cobrado': 'Collected', 'Ha pagado': 'Paid', 'Neto en mano': 'Net in hand',
    '(sin asignar)': '(unassigned)', 'Estáis en paz.': 'You are even.', 'Nuevo movimiento': 'New movement', 'Gasto': 'Expense', 'Ingreso': 'Income',
    'Importe €': 'Amount €', 'gasto': 'expense', 'ingreso': 'income', '¿Borrar movimiento?': 'Delete movement?', 'Apuntado': 'Saved',
    'Filamento': 'Filament', 'Resina': 'Resin', 'Repuestos': 'Spare parts', 'Embalaje': 'Packaging', 'Envíos': 'Shipping', 'Herramientas': 'Tools',
    'Comisiones': 'Fees', 'Otros': 'Other', 'Ventas': 'Sales',

    // --- extracto
    'Sale de los pedidos (sin presupuestos ni cancelados), agrupados por mes de creación. Usa el desglose guardado al crear cada línea, así que no cambia si luego tocas precios en Ajustes.':
      'Built from orders (excluding quotes and cancelled ones), grouped by creation month. Uses the breakdown saved with each line, so it does not change if you edit prices later.',
    'Mes a mes': 'Month by month', 'Pedidos': 'Orders', 'Piezas': 'Pieces', 'IVA repercutido': 'VAT charged', 'Horas máquina': 'Machine hours',
    'kWh': 'kWh', 'Luz': 'Electricity', 'Horas mano obra': 'Labour hours', 'Coste total': 'Total cost', 'Beneficio': 'Profit',
    'Luz ya apuntada en contabilidad': 'Electricity already booked', 'Líneas sin desglose': 'Lines without breakdown', 'Sin pedidos este año': 'No orders this year',
    'Por impresora': 'By printer', 'Material consumido': 'Material used', 'Por canal': 'By channel', 'Ya apuntado en contabilidad:': 'Already booked:',
    'Apuntar luz como gasto': 'Book electricity as expense', 'Actualizar luz como gasto': 'Update electricity expense', 'Coste laminador': 'Slicer cost',

    // --- impresoras
    'Imprimiendo': 'Printing', 'En pausa': 'Paused', 'Terminada': 'Finished', 'Libre': 'Idle', 'Cancelada': 'Cancelled', 'Sin trabajo': 'No job',
    'Historial e impresiones reales': 'History & actual prints', 'Se actualiza cada 10 s.': 'Refreshes every 10 s.', 'vía puente': 'via bridge',
    'No hay impresoras conectadas. Configúralas en': 'No printers connected. Set them up in', 'Ajustes → Impresoras': 'Settings → Printers',
    '(Conexión: Moonraker + IP).': '(Connection: Moonraker + IP).', 'Pide a un administrador que las configure.': 'Ask an admin to set them up.',
    'Asigna cada impresión a su pedido para guardar el tiempo y el filamento': 'Assign each print to its order to store the', 'reales': 'actual',
    'junto a lo estimado.': 'time and filament next to the estimate.', 'Fin': 'End', 'Archivo': 'File', 'Real': 'Actual', 'Estimado': 'Estimated',
    'Filamento': 'Filament', 'Pedido': 'Order', 'Desasignada': 'Unassigned', 'No hay impresoras conectadas': 'No printers connected', 'Enviando…': 'Sending…',

    // --- catálogo y stock
    'Stock de material': 'Material stock', 'Se descuenta solo cuando un pedido pasa a': 'Deducted automatically when an order moves to',
    '(y vuelve si lo cancelas). Para empezar a controlar un material, haz un': '(and returned if you cancel it). To start tracking a material, do an',
    'Ajuste': 'Adjustment', 'con lo que te queda o registra una': 'with what you have left or record a', 'Compra': 'Purchase', '+ Compra': '+ Purchase',
    'Queda': 'Left', 'Envases aprox.': 'Approx. spools', 'sin controlar': 'not tracked', 'bajo': 'low', 'Recalcular todos los precios': 'Recalculate all prices',
    'Piezas que vendéis a menudo. Cárgalas en la calculadora para recalcular con los precios actuales o añádelas directas a un pedido. Los': 'Pieces you sell often. Load them into the calculator to reprice them or add them straight to an order. Your',
    'Piezas que vendéis a menudo. Cárgalas en la calculadora para recalcular con los precios actuales o añádelas directas a un pedido. Lo marcado como':
      'Pieces you sell often. Load them into the calculator to reprice them or add them straight to an order. Items marked as',
    'público': 'public', 'es lo que aparecerá en la futura tienda online.': 'are what will show in the future online store.',
    'Guarda productos desde la calculadora': 'Save products from the calculator', 'Tienda': 'Store', 'pública': 'public', 'bajo pedido': 'made to order',
    'web': 'web', 'Actualizar precio': 'Update price', 'Referencia (SKU)': 'Reference (SKU)', 'Precio interno €': 'Internal price €', 'Coste €': 'Cost €',
    'Precio público € (vacío = interno)': 'Public price € (empty = internal)', 'Stock (vacío = bajo pedido)': 'Stock (empty = made to order)',
    'Días de fabricación': 'Lead time (days)', 'Descripción (la verá el cliente)': 'Description (customer facing)', 'Notas internas': 'Internal notes',
    'Archivos del modelo': 'Model files', 'Público en tienda': 'Public in store', 'Producto guardado': 'Product saved', '¿Borrar producto?': 'Delete product?',
    'Sin archivos. Al añadir este producto a un pedido, el pedido hereda sus archivos.': 'No files. When this product is added to an order, the order inherits its files.',
    'Entrada registrada': 'Purchase recorded', 'Entrada registrada y gasto apuntado': 'Purchase and expense recorded', 'Stock ajustado': 'Stock adjusted',
    'Ningún precio ha cambiado': 'No price changed',
    'Recalcula precio y coste de todos los productos con los ajustes actuales (margen, luz, materiales…). ¿Seguir?':
      'Recalculate price and cost of every product with the current settings (margin, electricity, materials…)? Continue?',
    '¿Cuánto habéis pagado en total (€)? Deja vacío para no apuntar el gasto.': 'How much did you pay in total (€)? Leave empty to skip the expense.',

    // --- ajustes
    'Mi cuenta': 'My account', 'Contraseña actual': 'Current password', 'Nueva (mín. 8)': 'New (min. 8)', 'Repite la nueva': 'Repeat new',
    'Cambiar contraseña': 'Change password', 'Contraseña cambiada': 'Password changed', 'Las contraseñas nuevas no coinciden': 'New passwords do not match',
    'Usuarios': 'Users', 'Administrador': 'Admin', ': todo, incluidos ajustes, impresoras, materiales, marca, usuarios y actualizaciones.':
      ': everything, including settings, printers, materials, branding, users and updates.',
    ': calculadora, pedidos, contabilidad, extracto, catálogo y stock.': ': calculator, orders, accounting, report, catalog and stock.',
    '(tú)': '(you)', 'Nuevo usuario': 'New user', 'Usuario creado': 'User created', 'Rol cambiado': 'Role changed',
    'Tienda y marca': 'Shop & branding', 'Eslogan': 'Tagline', 'Color principal': 'Accent colour',
    'Logo (PNG/JPG/WEBP, mejor con fondo transparente)': 'Logo (PNG/JPG/WEBP, ideally transparent)',
    'Favicon (PNG/ICO cuadrado; si no hay, se usa el logo)': 'Favicon (square PNG/ICO; the logo is used if empty)',
    'Datos para presupuestos y albaranes': 'Details for quotes and delivery notes', 'Nombre / razón social': 'Name / company', 'NIF': 'Tax ID',
    'Web / Instagram': 'Website / Instagram', 'Pie de los documentos': 'Document footer', 'Validez presupuestos (días)': 'Quote validity (days)',
    'Tienda online (preparado para el futuro)': 'Online store (groundwork)', 'Publicar el catálogo público en': 'Publish the public catalog at',
    'Guardar marca': 'Save branding', 'Marca guardada': 'Branding saved', 'Costes generales': 'General costs', 'Precio luz €/kWh': 'Electricity €/kWh',
    'Preparación €/h': 'Preparation €/h', 'Postprocesado €/h': 'Post-processing €/h', 'Merma material %': 'Material waste %', 'Riesgo de fallo %': 'Failure risk %',
    'IVA %': 'VAT %', 'Comisión fija €': 'Fixed fee €', 'Tipo de venta': 'Sale type', 'Aplicar': 'Apply',
    'Personas (separadas por coma)': 'People (comma separated)', 'Canales de venta': 'Sales channels', 'Categorías de gasto': 'Expense categories',
    'Guardar ajustes': 'Save settings', 'Ajustes guardados. Recalcula los precios del catálogo si hace falta.': 'Settings saved. Recalculate catalog prices if needed.',
    'Horas/día': 'Hours/day', 'Amortizar (meses)': 'Depreciate (months)', 'Mant. €/mes': 'Maint. €/month', 'Conexión': 'Connection',
    'Puente': 'Bridge', 'IP / nombre': 'IP / host', 'API key': 'API key', '(opcional)': '(optional)', 'Ninguna': 'None',
    'Moonraker (directa)': 'Moonraker (direct)', 'Probar': 'Test', 'Precio envase €': 'Spool price €',
    ': elige Moonraker (Klipper) y pon la': ': choose Moonraker (Klipper) and enter the', 'IP o nombre': 'IP or hostname',
    'de esa impresora (puerto 7125 por defecto, o': 'of that printer (port 7125 by default, or', 'ip:puerto': 'ip:port',
    '). La API key solo si Moonraker la pide. Sin conexión, la impresora sirve igual para calcular precios.': '). API key only if Moonraker requires it. Without a connection the printer still works for pricing.',
    'Precio del envase y cantidad que trae (g para filamento, ml para resina). «Aviso» = cantidad por debajo de la cual sale la alerta de stock bajo.':
      'Spool/bottle price and how much it holds (g for filament, ml for resin). “Alert” = level below which the low-stock warning shows.',
    'Puentes (impresoras en otra red)': 'Bridges (printers on another network)', 'Si las impresoras están en otra red que este servidor (otra casa, otro taller), instala un':
      'If your printers are on a different network from this server (another house, another workshop), install a',
    'puente': 'bridge', 'en un equipo de esa red (Raspberry Pi, NAS, mini PC). El puente se conecta hacia esta web, así que no hace falta VPN. Luego, en la impresora, elige Conexión «Puente», el puente y su IP local.':
      'on a machine in that network (Raspberry Pi, NAS, mini PC). The bridge connects out to this site, so no VPN is needed. Then set the printer to Connection “Bridge”, pick the bridge and its local IP.',
    'Nombre del puente': 'Bridge name', 'p.ej. Casa / Taller': 'e.g. Home / Workshop', 'Crear puente': 'Create bridge', 'Sin puentes.': 'No bridges.',
    'conectado': 'connected', 'desconectado': 'disconnected', 'sin estrenar': 'never connected', 'ninguna': 'none', 'Versión': 'Version', 'Copiado': 'Copied',
    'Copiar comando': 'Copy command', 'Elige el puente de esa impresora': 'Choose the bridge for that printer', 'Pon la IP o el nombre de la impresora': 'Enter the printer IP or hostname',
    '¿Borrar el puente? Sus impresoras se quedarán sin conexión.': 'Delete the bridge? Its printers will go offline.', '¿Borrar?': 'Delete?', 'Guardado': 'Saved',

    // --- mantenimiento
    'Actualizaciones': 'Updates', 'Versión instalada:': 'Installed version:', 'Canal de actualización': 'Update channel',
    'Versiones publicadas (estable, firmadas)': 'Published releases (stable, signed)', 'Rama main (lo último del repo)': 'main branch (latest code)',
    'Instala las versiones que se publican en GitHub (Releases). Es lo recomendado.': 'Installs the versions published on GitHub (Releases). Recommended.',
    'Instala el último cambio subido a la rama main, sin esperar a una versión. Sin firma: solo para quien sigue el desarrollo.':
      'Installs the latest change on the main branch without waiting for a release. Unsigned: for people following development.',
    'O sube un paquete a mano (.mtc, .tar o .tar.gz)': 'Or upload a package manually (.mtc, .tar or .tar.gz)', 'Tu contraseña': 'Your password',
    'Subir y actualizar': 'Upload and update', 'Volver a la anterior': 'Roll back',
    'Antes de instalar se hace copia de la base de datos. Si la versión nueva no arranca, vuelve sola a la anterior. Los datos no se tocan.':
      'The database is backed up before installing. If the new version does not start, it rolls back automatically. Your data is never touched.',
    'Sin actualizaciones todavía.': 'No updates yet.', 'Petición enviada, esperando al aplicador…': 'Request sent, waiting for the updater…',
    'Consultando GitHub…': 'Checking GitHub…', 'comprobar de nuevo': 'check again', 'ver commit': 'view commit', 'novedades': 'release notes',
    'Elige el paquete': 'Choose the package', 'Pon tu contraseña': 'Enter your password', 'Volviendo a la anterior…': 'Rolling back…',
    'Tu contraseña para volver a la versión anterior:': 'Your password to roll back:', 'Sin repositorio configurado: sube el paquete a mano.': 'No repository configured: upload the package manually.',
    'El aplicador no está instalado: actualiza una vez desde el host con': 'The updater is not installed: update once from the host with',
    'Copias de seguridad': 'Backups', 'Se hace una copia automática de la base de datos cada día (se guardan 30) y otra antes de cada actualización, en':
      'The database is backed up automatically every day (30 kept) and before every update, in', 'dentro del LXC.': 'inside the LXC.',
    'Descargar copia de la base de datos': 'Download database backup', 'Movimientos (CSV)': 'Movements (CSV)',
    'Los archivos de los pedidos (STL/3MF) están en': 'Order files (STL/3MF) live in', ': para tenerlos a salvo, incluye el LXC en los backups de Proxmox.': ': include the LXC in your Proxmox backups to keep them safe.',
    'Historial': 'History',

    // --- 0.6: almacén, estados, Telegram, fallos, conjuntos
    'Almacén': 'Stock room', 'Colores que tienes': 'Colours you have', 'ver gastadas': 'show used up', '¿Lo puedo imprimir con lo que tengo?': 'Can I print it with what I have?',
    'Pon los colores y gramos que pide el modelo, o impórtalos de la calculadora tras soltar su 3MF/G-code.': 'Enter the colours and grams the model needs, or import them from the calculator after dropping its 3MF/G-code.',
    '+ color': '+ colour', 'Usar lo del laminador': 'Use slicer data', 'Comprobar': 'Check', 'Añadir bobinas': 'Add spools', 'Marca': 'Brand',
    'Sunlu, eSun, Bambu…': 'Sunlu, eSun, Bambu…', 'Negro, Rojo fuego…': 'Black, Fire red…', 'Tono': 'Shade', 'Peso neto (g / ml)': 'Net weight (g / ml)',
    'Bobina vacía (g)': 'Empty spool (g)', 'si la sabes': 'if you know it', 'Cuántas': 'How many', 'Ubicación': 'Location', 'Estante 2, caja A…': 'Shelf 2, box A…',
    'Pagado en total € (opcional)': 'Total paid € (optional)', 'Quién pagó': 'Paid by', 'Añadir al almacén': 'Add to stock', 'Bobinas': 'Spools',
    'Lo que queda se descuenta solo al imprimir (y en los fallos). Para afinar,': 'What is left is deducted automatically when printing (and on failures). To fine-tune it,',
    'pésala': 'weigh it', ': lo que queda = peso − bobina vacía. Al gastar o borrar una bobina, pesa la bobina vacía y se guarda para esa marca.':
      ': left = weight − empty spool. When a spool is used up or deleted, weigh the empty spool and it is saved for that brand.',
    'Por material': 'By material', 'Bobinas vacías por marca': 'Empty spools by brand', 'Se aprende sola al gastar bobinas; también puedes ponerla a mano.': 'Learned automatically when spools run out; you can also enter it by hand.',
    'Ninguna todavía.': 'None yet.', 'Material (PLA…)': 'Material (PLA…)', 'Sin bobinas.': 'No spools.', 'Aún no hay bobinas. Añádelas abajo.': 'No spools yet. Add them below.',
    'Pesar': 'Weigh', 'Editar': 'Edit', 'Gastada / borrar': 'Used up / delete', 'abierta': 'open', 'cerrada': 'sealed', 'gastada': 'used up', 'Queda': 'Left',
    'Bobina': 'Spool', 'Si puedes,': 'If you can,', 'pesa la bobina vacía': 'weigh the empty spool', ': se guardará para': ': it will be saved for',
    'y la próxima vez sabrás cuánto queda en una bobina de esa marca solo con pesarla.': 'and next time you will know what is left on a spool of that brand just by weighing it.',
    'Peso de la bobina vacía (g)': 'Empty spool weight (g)', 'p. ej. 180': 'e.g. 180', 'Marcar como gastada': 'Mark as used up',
    'bobina: automática': 'spool: automatic', 'sin bobinas en el almacén': 'no spools in stock', 'sin color': 'no colour', 'ir al almacén': 'go to stock room', 'ver almacén': 'see stock room',
    '✓ Tienes todos los colores en el almacén.': '✓ You have every colour in stock.', 'Te falta algún color o cantidad:': 'Missing a colour or quantity:',
    '✓ Lo puedes imprimir con lo que tienes': '✓ You can print it with what you have', '✗ Te falta algo': '✗ Something is missing',
    'lo tienes': 'you have it', 'algo parecido': 'something similar', 'no lo tienes': 'you don’t have it', 'mismo color': 'same colour', 'parecido': 'similar',
    'distinto': 'different', 'otro material': 'other material', 'no llega': 'not enough',
    'Guardado el peso de la bobina vacía para esa marca': 'Empty spool weight saved for that brand', 'Bobina borrada': 'Spool deleted', 'Bobina gastada': 'Spool used up',
    '¿Borrar la bobina del almacén? (si solo se ha gastado, mejor «Marcar como gastada» para conservar el historial)': 'Delete the spool? (if it is just used up, “Mark as used up” keeps the history)',
    'Primero suelta el 3MF o G-code en la calculadora': 'Drop the 3MF or G-code in the calculator first', 'Nombre del color': 'Colour name',
    '¿Cuánto pesa ahora la bobina entera (g)?': 'How much does the whole spool weigh now (g)?',
    'elige el material': 'choose the material', 'peso no válido': 'invalid weight', 'falta el peso de la bobina vacía de esta marca': 'the empty spool weight for this brand is missing',
    'marca y peso obligatorios': 'brand and weight are required',
    // estados
    'recibido': 'received', 'programado': 'scheduled', 'postprocesado': 'post-processing', 'recibido ·': 'received ·', 'programado ·': 'scheduled ·', 'postprocesado ·': 'post-processing ·',
    'lleva demasiado en este estado': 'too long in this status', 'Historial de estados': 'Status history',
    // fallos
    'Fallo': 'Failed', 'La impresión falló: apunta lo que se ha perdido': 'The print failed: record what was lost', 'Fallos de impresión': 'Print failures',
    'Fallo apuntado: material descontado del stock': 'Failure recorded: material deducted from stock', 'Fallo apuntado': 'Failure recorded',
    '¿Borrar este fallo? El material vuelve al stock.': 'Delete this failure? The material goes back to stock.', 'Ha fallado': 'It failed',
    '¿Qué pasó? (opcional: despegue, espagueti, atasco, corte de luz…)': 'What happened? (optional: warping, spaghetti, clog, power cut…)',
    '¿Qué pasó? (opcional)': 'What happened? (optional)', 'Porcentaje al que se paró': 'Percentage when it stopped', 'No hay pedidos en «imprimiendo»': 'No orders in “printing”',
    'porcentaje no válido (1-100)': 'invalid percentage (1-100)', 'línea no válida': 'invalid line',
    'esa línea no tiene cálculo (se metió a mano): no sé qué gastaba': 'that line has no calculation (entered by hand): I don’t know what it used',
    // conjuntos
    'conjunto': 'kit', '+ Nuevo conjunto': '+ New kit', 'Piezas del conjunto': 'Kit pieces', '+ añadir pieza del catálogo…': '+ add piece from catalog…',
    'Pieza': 'Piece', 'color, relleno…': 'colour, infill…', 'Material extra necesario': 'Extra parts needed', '— muelles, tornillos, imanes, pintura…': '— springs, screws, magnets, paint…',
    'Cant.': 'Qty', '€/ud': '€/unit', 'Muelle 0,8 mm': 'Spring 0.8 mm', '+ material extra': '+ extra part', 'Usar precio sugerido': 'Use suggested price',
    'Instrucciones (montaje, pintura, consejos…)': 'Instructions (assembly, painting, tips…)', '1. Imprime el cuerpo con la abertura hacia arriba…': '1. Print the body opening up…',
    'Descargar todo (.zip)': 'Download all (.zip)', 'Añade las piezas que lo forman.': 'Add the pieces it is made of.',
    'agrupan varias piezas (p. ej. una granada: cuerpo, tapa, anilla…) con su material extra e instrucciones. Lo marcado como':
      'group several pieces (e.g. a grenade: body, cap, ring…) with their extra parts and instructions. Items marked as', 'conjuntos': 'kits',
    'Nombre del conjunto (p. ej. Granada de airsoft M67)': 'Kit name (e.g. airsoft grenade M67)', 'precio sugerido': 'suggested price',
    // Telegram
    'Avisos por Telegram': 'Telegram alerts', '1) Crea un bot con': '1) Create a bot with', 'y copia el token. 2) Escríbele': 'and copy the token. 2) Send it',
    '(o añádelo a vuestro grupo). 3) Pulsa «Buscar mi chat». Se revisa cada 10 minutos.': '(or add it to your group). 3) Press “Find my chat”. Checked every 10 minutes.',
    'Avisos activados': 'Alerts on', 'Token del bot': 'Bot token', 'Chat': 'Chat', 'id del chat': 'chat id', 'Buscar mi chat': 'Find my chat',
    'Dirección de la web (para los enlaces de los avisos)': 'Website address (for links in alerts)', 'Recordar cada (horas)': 'Remind every (hours)',
    'Avisar si un pedido lleva más de… (horas) en el estado': 'Alert when an order stays longer than… (hours) in status', 'sin límite': 'no limit',
    'Pedido nuevo': 'New order', 'Entrega hoy/mañana o pasada': 'Due today/tomorrow or late', 'Guardar avisos': 'Save alerts', 'Enviar prueba': 'Send test',
    'Avisos guardados': 'Alerts saved', 'Mensaje enviado: mira Telegram': 'Message sent: check Telegram',
    'El bot no ha recibido mensajes: escríbele /start y vuelve a pulsar': 'The bot has no messages: send it /start and press again', '¿Qué chat?': 'Which chat?',
    'falta el token del bot o el chat': 'bot token or chat missing', 'token del bot no válido': 'invalid bot token', 'chat no válido (¿has escrito /start al bot?)': 'invalid chat (did you send /start to the bot?)',
    'el bot no puede escribir en ese chat': 'the bot cannot write to that chat', 'pon primero el token del bot': 'enter the bot token first',
    'Piezas impresas a medida': '3D prints made to order',

    // --- 0.7: mantenimiento, clientes, venta en puestos
    'Bobina vacía': 'Empty spool', 'Venta': 'Sell', 'Clientes': 'Customers', 'Sistema': 'System', 'Venta rápida': 'Quick sale', 'Puestos abiertos': 'Open stalls',
    '+ Nuevo cliente': '+ New customer', '+ Nuevo puesto': '+ New stall', '+ Otro importe': '+ Other amount', '+ Tarea': '+ Task', 'Editar puesto': 'Edit stall',
    'Puesto': 'Stall', 'Buscar producto…': 'Search product…', 'Forma de pago': 'Payment method', 'Cobra': 'Taken by', 'Cliente (opcional)': 'Customer (optional)',
    'anónimo': 'anonymous', 'Cobrar': 'Charge', 'Efectivo': 'Cash', 'Tarjeta': 'Card', 'Bizum': 'Bizum', 'Transferencia': 'Bank transfer', 'Otro': 'Other',
    'Lo que llevas al puesto': 'What you take to the stall', 'Llevas': 'Taken', 'Vendidas': 'Sold', 'Vuelven': 'Coming back',
    'Apunta cuántas llevas de cada cosa y al cerrar sabrás qué tiene que volver.': 'Note how many of each you take; when you close you will know what should come back.',
    'Ventas': 'Sales', 'Sin ventas.': 'No sales.', 'Sin ventas todavía.': 'No sales yet.', 'Pago': 'Payment', 'Hora': 'Time', 'Deshacer': 'Undo',
    'Toca los productos para añadirlos.': 'Tap products to add them.', 'Precio por unidad': 'Unit price', '€/ud': '€/unit', 'quedan': 'left',
    'Venta suelta': 'Loose sale', 'Sin puesto (venta suelta en mano)': 'No stall (loose sale in person)', 'Elige un puesto.': 'Choose a stall.',
    'Crea un puesto (mercadillo, feria, quedada…) para ver la caja, lo vendido y lo que te ha costado.': 'Create a stall (market, fair, meetup…) to see the cash box, what you sold and what it cost you.',
    'debería haber en caja': 'should be in the cash box', 'Cerrar puesto y contar caja': 'Close stall and count cash', 'Reabrir': 'Reopen',
    'abierto': 'open', 'cerrado': 'closed', 'Venta anónima': 'Anonymous sale', 'Para stock': 'For stock', 'Puesto / en mano': 'Stall / in person',
    'Fabricar para stock': 'Make for stock', 'Guardado': 'Saved', 'Elige un puesto': 'Choose a stall', '✓ cuadra': '✓ balances',
    'Se crean solos al hacer un pedido con nombre. Las ventas en puestos sin nombre van como «Venta anónima» y no crean ficha.':
      'Created automatically when an order has a name. Stall sales without a name are recorded as “Anonymous sale” and get no card.',
    'Contacto': 'Contact', 'Gastado': 'Spent', 'Debe': 'Owes', 'Último': 'Last', 'Nadie coincide con la búsqueda.': 'Nobody matches the search.',
    'Aún no hay clientes.': 'No customers yet.', 'Nuevo cliente': 'New customer', 'Teléfono / contacto': 'Phone / contact', 'Dirección': 'Address',
    'prefiere PETG, viene los sábados…': 'prefers PETG, comes on Saturdays…', 'gastado': 'spent', 'pendiente de cobro': 'pending payment', 'último pedido': 'last order',
    'Borrar ficha': 'Delete card', 'Nuevo pedido': 'New order', 'Repetir el último': 'Repeat the last one', 'sin cobrar': 'unpaid', 'Sin pedidos.': 'No orders.',
    'Falta el nombre': 'Name missing', '¿Borrar la ficha? Los pedidos se quedan, pero sin enlazar.': 'Delete the card? Orders stay, but unlinked.',
    // mantenimiento
    'Mantenimiento de impresoras': 'Printer maintenance', 'Cuenta las horas con Moonraker o, si no hay conexión, con los pedidos y los fallos':
      'Counts hours from Moonraker or, without a connection, from orders and failures', 'horas de Moonraker': 'Moonraker hours', 'horas de pedidos y fallos': 'hours from orders and failures',
    'Hecho': 'Done', 'Sumar horas': 'Add hours', 'Historial': 'History', 'Modelo (perfil)': 'Model (profile)', 'Cargar tareas': 'Load tasks',
    'Horas: Moonraker': 'Hours: Moonraker', 'Horas: pedidos y fallos': 'Hours: orders and failures', 'toca': 'due', 'pronto': 'soon',
    'Sin tareas. Elige el modelo de la impresora para cargar las recomendadas por el fabricante.': 'No tasks. Choose the printer model to load the maker’s recommended ones.',
    'Añade tus impresoras en Ajustes.': 'Add your printers in Settings.', 'Tarea de mantenimiento': 'Maintenance task', 'Tarea': 'Task', 'Engrasar husillos': 'Grease lead screws',
    'Avisa con lo que llegue antes. Deja vacío lo que no uses.': 'Alerts on whichever comes first. Leave blank what you don’t use.',
    'Cada (horas de impresión)': 'Every (print hours)', 'Cada (impresiones)': 'Every (prints)', 'Cada (días)': 'Every (days)', 'Hecho por última vez': 'Last done',
    'Horas sumadas a mano': 'Hours added by hand', 'Nada apuntado todavía.': 'Nothing recorded yet.', 'Apuntado': 'Recorded', 'Tareas cargadas': 'Tasks loaded',
    'Elige el modelo': 'Choose the model', '¿Borrar esta tarea?': 'Delete this task?', 'Quién': 'Who', 'Qué': 'What',
    '¿Alguna nota? (opcional: qué has cambiado, qué grasa…)': 'Any note? (optional: what you changed, which grease…)',
    'Horas a sumar (p. ej. lo que ya llevaba la impresora antes de usar MiTallercito, o impresiones sin pedido)': 'Hours to add (e.g. what the printer already had before MiTallercito, or prints without an order)',
    'Nota (opcional)': 'Note (optional)', '¿Cuándo le hiciste mantenimiento por última vez? (AAAA-MM-DD; vacío = hoy)': 'When did you last service it? (YYYY-MM-DD; blank = today)',
    '¿Sustituir las tareas que ya tiene? (Cancelar = solo añadir las que falten)': 'Replace its current tasks? (Cancel = only add the missing ones)',
    'Mantenimiento de impresoras ': 'Printer maintenance ', '¿Qué es?': 'What is it?', 'Precio €': 'Price €', 'Varios': 'Misc.',
    '¿Deshacer esta venta? Lo vendido vuelve al stock.': 'Undo this sale? The items go back to stock.', 'Puesto cerrado': 'Stall closed',
    '¿Cuánto cuesta el puesto? € (0 si nada)': 'How much does the stall cost? € (0 if nothing)', '¿Con cuánto cambio empiezas en la caja? €': 'How much change do you start with? €',
    'Nombre': 'Name', 'Lugar': 'Place', 'Fecha (AAAA-MM-DD)': 'Date (YYYY-MM-DD)', 'Coste del puesto €': 'Stall cost €', 'Cambio inicial €': 'Starting change €',
    'Nombre del puesto (p. ej. Mercadillo medieval de Toledo)': 'Stall name (e.g. Toledo medieval market)',
    'OctoPrint': 'OctoPrint', 'PrusaLink': 'PrusaLink', 'Moonraker / Klipper': 'Moonraker / Klipper', 'Puente (Moonraker)': 'Bridge (Moonraker)',
    'API key. En PrusaLink también vale usuario:contraseña (maker:…)': 'API key. For PrusaLink, user:password (maker:…) also works',
    'Mantenimiento de impresoras (Telegram)': 'Printer maintenance (Telegram)',
    // perfiles
    'FDM genérica (Klipper, Voron, Ender…)': 'Generic FDM (Klipper, Voron, Ender…)', 'Resina (Anycubic Photon, Elegoo Mars/Saturn…)': 'Resin (Anycubic Photon, Elegoo Mars/Saturn…)',
    'Limpiar y lubricar ejes y husillos': 'Clean and lubricate axes and lead screws', 'Habitual cada 200-300 h o cada 1-3 meses (orientativo)': 'Usually every 200-300 h or every 1-3 months (guideline)',
    'Revisar tensión de correas': 'Check belt tension', 'Orientativo': 'Guideline', 'Revisar tornillería, poleas y conectores': 'Check screws, pulleys and connectors',
    'Limpiar ventiladores y restos de plástico': 'Clean fans and plastic debris', 'Revisar tubo PTFE y disipador': 'Check PTFE tube and heatsink', 'Cambiar boquilla': 'Replace nozzle',
    'Latón: 500-1000 h; acero endurecido: 2000 h o más': 'Brass: 500-1000 h; hardened steel: 2000 h or more', 'Latón: 500-1000 h': 'Brass: 500-1000 h',
    'Lubricar la guía del eje Y': 'Lubricate the Y-axis rail', 'Bambu: una vez al mes y cuando la impresora lo pida (≈150 h)': 'Bambu: once a month and when the printer asks (≈150 h)',
    'Limpiar y lubricar ejes X, Y y Z': 'Clean and lubricate X, Y and Z axes', 'Cada 200-300 h o si se ven sucios': 'Every 200-300 h or when they look dirty',
    'Engrasar husillo(s) Z': 'Grease Z lead screw(s)', 'Bambu: cada 3 meses': 'Bambu: every 3 months', 'Lubricar la polea tensora del eje Y': 'Lubricate the Y idler pulley',
    'Limpiar varillas de carbono del eje X (sin grasa)': 'Clean X-axis carbon rods (no grease)', 'Bambu: no lubricar, solo limpiar': 'Bambu: do not lubricate, only clean',
    'Limpiar varillas de los ejes Y y Z': 'Clean Y and Z rods', 'Bambu: cada mes (con ABS/ASA, cada 5 kg)': 'Bambu: monthly (with ABS/ASA, every 5 kg)',
    'Antióxido en varillas Y y Z': 'Anti-rust on Y and Z rods', 'Engrasar husillos Z': 'Grease Z lead screws', 'Cambiar filtro de carbón activo': 'Replace activated carbon filter',
    'Bambu: cada 3 meses a ~8 h/día; en producción, cada mes': 'Bambu: every 3 months at ~8 h/day; monthly in production',
    'Revisión de ejes y lubricación': 'Axes check and lubrication', 'Prusa: cada 200 h de impresión': 'Prusa: every 200 print hours',
    'Revisar conectores de la electrónica': 'Check electronics connectors', 'Prusa: cada 600-800 h': 'Prusa: every 600-800 h',
    'Inspección y mantenimiento general': 'General inspection and maintenance', 'Prusa: cada ~200-300 h': 'Prusa: every ~200-300 h', 'Lubricar husillos Z': 'Lubricate Z lead screws',
    'Prusa: cada ~500 h': 'Prusa: every ~500 h', 'Revisar placas electrónicas': 'Check electronics boards', 'Prusa: cada ~600-800 h': 'Prusa: every ~600-800 h',
    'Engrasar ejes (zonas indicadas en el manual)': 'Grease axes (areas shown in the manual)', 'Creality: cada 300 h. K1C: no engrasar la varilla de carbono X': 'Creality: every 300 h. K1C: do not grease the X carbon rod',
    'Revisión general (correas, tornillería, boquilla)': 'General check (belts, screws, nozzle)', 'Manual: cada 500 h acumuladas': 'Manual: every 500 accumulated hours',
    'Limpiar restos del interior': 'Clean debris inside', 'Lubricar husillos, ejes y guías': 'Lubricate lead screws, axes and rails', 'Creality: cada 500 h acumuladas': 'Creality: every 500 accumulated hours',
    'Revisar correas y excéntricas': 'Check belts and eccentric nuts', 'Limpiar y lubricar varillas ópticas y rodamientos': 'Clean and lubricate linear rods and bearings', 'Snapmaker: mensual': 'Snapmaker: monthly',
    'Limpiar varillas de carbono (sin aceite ni grasa)': 'Clean carbon rods (no oil or grease)', 'Snapmaker: mensual, solo limpiar': 'Snapmaker: monthly, clean only',
    'Limpiar y engrasar husillo y tuerca (grasa de litio blanca)': 'Clean and grease lead screw and nut (white lithium grease)', 'Snapmaker: trimestral': 'Snapmaker: quarterly',
    'Limpiar y engrasar pernos y bolas de acero': 'Clean and grease steel pins and balls', 'Revisar tensión de correas (sin grasa)': 'Check belt tension (no grease)',
    'Engrasar husillo Z y lubricar varillas del eje Y': 'Grease Z lead screw and lubricate Y rods', 'Anycubic (serie Kobra): cada 3 meses, o antes si suena el eje Z': 'Anycubic (Kobra series): every 3 months, or sooner if the Z axis is noisy',
    'Revisar cuchilla del filamento y boquilla': 'Check filament cutter and nozzle', 'Anycubic: revisión periódica': 'Anycubic: periodic check', 'Limpiar ventiladores': 'Clean fans',
    'Lubricar ejes': 'Lubricate axes', 'Elegoo: cada 3 meses': 'Elegoo: every 3 months', 'Limpiar ventilador de capa y del disipador': 'Clean part-cooling and heatsink fans',
    'Revisar el cable del cabezal': 'Check the toolhead cable', 'Orientativo: fallo conocido hacia las 300-350 h': 'Guideline: known failure around 300-350 h',
    'Revisar film FEP': 'Check FEP film', 'Cada 10-15 impresiones': 'Every 10-15 prints', 'Cambiar film FEP': 'Replace FEP film',
    '≈40 impresiones (Anycubic: ~30.000 capas); antes si está rayado o turbio': '≈40 prints (Anycubic: ~30,000 layers); sooner if scratched or cloudy',
    'Filtrar resina y limpiar la cuba': 'Filter resin and clean the vat', 'Nivelar la plataforma': 'Level the platform', 'Limpiar el protector de la pantalla LCD': 'Clean the LCD screen protector',

    // --- 0.8: variantes, ofertas, etiquetas QR, Manyfold, previsión
    '+ Nueva oferta': '+ New offer', '+ variante': '+ variant', 'Variante': 'Variant', 'Variantes': 'Variants', 'Crear varias de golpe…': 'Add several at once…',
    '— colores, tamaños… cada una con su precio y su stock': '— colours, sizes… each with its own price and stock', '— el del producto —': '— the product’s —',
    'Con variantes, el stock del producto es la suma de las suyas. «Material» cambia el color que se gasta al fabricarla.': 'With variants, the product stock is the sum of theirs. “Material” changes which colour is used when making it.',
    'Es la suma del stock de las variantes': 'It is the sum of the variants’ stock', 'Pon nombre a todas las variantes': 'Name every variant',
    'Escribe las variantes separadas por comas (p. ej. Negro, Blanco, Rojo)': 'Type the variants separated by commas (e.g. Black, White, Red)',
    'Packs y ofertas': 'Bundles and offers', 'Oferta': 'Offer', 'Para': 'For', 'Dónde': 'Where', 'Pausar': 'Pause', 'Activar': 'Activate', 'Activa': 'Active',
    'Se aplican solas al cobrar en un puesto y, en los pedidos, con el botón «Aplicar ofertas». Cada unidad entra como mucho en una oferta.': 'Applied automatically when selling at a stall and, on orders, with the “Apply offers” button. Each unit counts for one offer at most.',
    'Sin ofertas. Ejemplos: «3 llaveros por 10 €», «la 2ª maceta a mitad de precio».': 'No offers. Examples: “3 keyrings for €10”, “second planter half price”.',
    'Llaveros, Black Friday…': 'Keyrings, Black Friday…', 'Tipo': 'Type', 'Pack: N unidades por X €': 'Bundle: N units for €X', 'La N-ésima con descuento': 'Nth unit discounted', 'Descuento %': 'Discount %',
    'Unidades': 'Units', 'Unidades del pack': 'Units in the bundle', 'A partir de la unidad nº': 'From unit no.', 'Precio del pack €': 'Bundle price €',
    'Descuento en esa unidad % (100 = gratis)': 'Discount on that unit % (100 = free)', 'Se aplica a': 'Applies to', 'Todo el catálogo': 'Whole catalog', 'Una categoría': 'A category', 'Un producto': 'A product',
    'Puestos y pedidos': 'Stalls and orders', 'Solo en puestos': 'Only at stalls', 'Solo en pedidos': 'Only on orders', 'puestos y pedidos': 'stalls and orders', 'solo puestos': 'stalls only', 'solo pedidos': 'orders only',
    'todo': 'everything', 'Oferta guardada': 'Offer saved', '¿Borrar esta oferta?': 'Delete this offer?', 'Aplicar ofertas': 'Apply offers', 'Ninguna oferta encaja con este pedido': 'No offer fits this order',
    'Etiquetas de las marcadas': 'Labels for selected', 'Etiquetas de todas': 'Labels for all', 'Etiqueta con QR': 'QR label', 'Marca alguna bobina': 'Select a spool', 'No hay bobinas': 'No spools',
    '¿Imprimir las etiquetas con QR de estas bobinas?': 'Print the QR labels for these spools?', 'Ir al almacén': 'Go to stock room', 'Esa bobina ya no existe': 'That spool no longer exists', 'Marcar todas': 'Select all',
    'Previsión': 'Forecast', 'Filamento': 'Filament', 'Lo que piden los pedidos aún sin imprimir frente a lo que te queda, y cuándo se acabará al ritmo de los últimos días.':
      'What unprinted orders need versus what you have, and when it will run out at the recent rate.', 'Pendiente': 'Pending', 'Tras los pedidos': 'After orders', 'Gasto/día': 'Use/day',
    'Se acaba': 'Runs out', 'Comprar': 'Buy', 'no llega': 'not enough', 'comprar': 'buy', 'ya no llega': 'already short', 'sin controlar': 'not tracked',
    'Ajustes de la previsión': 'Forecast settings', 'Días que tarda en llegar una compra': 'Days a purchase takes to arrive', 'Calcular el ritmo con los últimos (días)': 'Compute the rate over the last (days)',
    'Contar también los presupuestos': 'Also count quotes', 'Activa el control de stock en tus materiales o añade bobinas para ver la previsión.': 'Turn on stock tracking for your materials or add spools to see the forecast.',
    'Traer de Manyfold': 'Get from Manyfold', 'Abrir en Manyfold': 'Open in Manyfold', 'Buscar modelo…': 'Search model…', 'Buscar': 'Search', 'Traer los marcados': 'Get selected', 'Trayendo…': 'Fetching…',
    'Nada con ese nombre.': 'Nothing with that name.', 'Buscando…': 'Searching…', '← volver': '← back', 'Este modelo no tiene archivos.': 'This model has no files.', 'Marca algún archivo': 'Select a file',
    'Configura Manyfold en Ajustes': 'Set up Manyfold in Settings', 'Guarda el pedido primero': 'Save the order first', 'Dirección de Manyfold': 'Manyfold address',
    'Para buscar modelos de tu biblioteca y traer sus archivos a pedidos y productos. Habla': 'To search your model library and bring its files into orders and products.',
    'el servidor': 'The server', 'con Manyfold: el navegador y los clientes nunca lo ven. En Manyfold abre': 'talks to Manyfold: the browser and customers never see it. In Manyfold open',
    ', crea una aplicación con permiso': ', create an application with the', 'y copia su ID y su secreto. Sin credenciales solo se ven los modelos públicos.': 'scope and copy its ID and secret. Without credentials only public models are visible.',
    // --- errores del servidor
    'usuario o contraseña incorrectos': 'wrong username or password', 'contraseña incorrecta': 'wrong password', 'no autenticado': 'not logged in',
    'solo un administrador puede hacer esto': 'only an admin can do this', 'tiene que quedar al menos un administrador': 'there must be at least one admin',
    'no puedes borrarte a ti mismo': 'you cannot delete yourself', 'la contraseña actual no es correcta': 'current password is wrong', 'ya existe': 'already exists',
    'nombre no válido (letras, números, . - _)': 'invalid name (letters, numbers, . - _)', 'falta el cliente': 'customer is missing', 'falta el nombre': 'name is missing',
    'no existe': 'not found', 'estado no válido': 'invalid status', 'tipo o importe no válido': 'invalid type or amount', 'cantidad no válida': 'invalid quantity',
    'número de envases no válido': 'invalid number of spools', 'no hay consumo ese mes': 'no usage that month', 'mes no válido': 'invalid month',
    'formato no válido (usa PNG, JPG, WEBP, GIF o ICO)': 'invalid format (use PNG, JPG, WEBP, GIF or ICO)', 'imagen demasiado grande (máx. 5 MB)': 'image too large (max. 5 MB)',
    'tipo no admitido (STL, 3MF, OBJ, STEP, G-code, resina, ZIP…)': 'file type not allowed (STL, 3MF, OBJ, STEP, G-code, resin, ZIP…)',
    'no se ha enviado archivo': 'no file sent', 'no se ha enviado el paquete': 'no package sent', 'paquete demasiado grande': 'package too large',
    'no es un paquete .tar / .tar.gz válido': 'not a valid .tar / .tar.gz package', 'el paquete no es de MiTallercito (falta VERSION o app.py)': 'not a MiTallercito package (VERSION or app.py missing)',
    'solo se pueden enviar G-code (.gcode). Desde un 3MF, exporta el G-code de la placa.': 'only G-code (.gcode) can be sent. From a 3MF, export the plate G-code.',
    'la tienda ya está configurada': 'the shop is already set up', 'nombre de usuario no válido': 'invalid username',
    'código de instalación no válido (míralo en la salida del instalador o con «mitallercito setup-token»)': 'invalid setup code (see the installer output or run “mitallercito setup-token”)',
    'impresora o archivo no existe': 'printer or file not found', 'pedido no existe': 'order not found', 'producto no existe': 'product not found',
    'esta instalación solo acepta versiones firmadas: usa el canal «Versiones publicadas»': 'this installation only accepts signed releases: use the “Published releases” channel',
    'no hay versiones publicadas todavía': 'no releases published yet', 'no hay repositorio configurado': 'no repository configured',
    'la impresora no tiene conexión configurada': 'the printer has no connection configured', 'no tiene puente asignado': 'no bridge assigned',
    'el puente aún no ha informado de esta impresora': 'the bridge has not reported this printer yet', 'no autorizado: revisa la API key': 'unauthorised: check the API key',
    'respuesta no válida (¿es Moonraker?)': 'invalid response (is it Moonraker?)', 'token de puente no válido': 'invalid bridge token',
    'en Docker se actualiza con «docker compose pull && docker compose up -d»': 'in Docker, update with “docker compose pull && docker compose up -d”',
    // --- v0.9: menú, diálogos, buscador, compra, gastos fijos
    'Vender': 'Sell', 'Taller': 'Workshop', 'Cuentas': 'Money', 'Más': 'More', 'Buscar…': 'Search…', 'Buscar': 'Search', 'Menú': 'Menu', 'Salir': 'Log out',
    'Aceptar': 'OK', 'Vale': 'OK', 'Acciones': 'Actions', 'Bobinas': 'Spools', 'Puestos': 'Stalls',
    'Busca pedidos, clientes, productos, bobinas… o escribe una acción': 'Search orders, customers, products, spools… or type an action',
    '↑↓ moverse · Enter abrir · Esc cerrar': '↑↓ move · Enter open · Esc close',
    'Nuevo pedido': 'New order', 'Venta en el puesto': 'Sell at the stall', 'Nuevo cliente': 'New customer', 'Apuntar gasto o ingreso': 'Add expense or income',
    'Lista de la compra': 'Shopping list', 'Nuevo gasto fijo': 'New fixed expense', 'Calculadora de precio': 'Price calculator',
    'Copiar lista': 'Copy list', '+ Añadir': '+ Add', 'Comprado hace poco': 'Bought recently', 'Nada todavía.': 'Nothing yet.',
    'No hay nada apuntado. Añade lo que haga falta o usa lo que sugiere la previsión.': 'Nothing on the list. Add what you need or use what the forecast suggests.',
    'La previsión sugiere:': 'The forecast suggests:', 'Qué': 'What', 'Cuánto': 'How much', 'Precio/ud': 'Price/unit', 'Comprado': 'Bought',
    'Total estimado:': 'Estimated total:', 'Añadir a la lista': 'Add to the list', 'Editar compra': 'Edit item', 'Quitar de la lista': 'Remove from the list',
    'Si no es un material: ¿qué es?': 'If it is not a material: what is it?', '— otra cosa —': '— something else —', 'Envases / unidades': 'Packs / units',
    'Precio por unidad (€)': 'Price per unit (€)', 'Vacío = el de la última compra.': 'Empty = the last purchase price.', 'Nota': 'Note',
    'enlace, oferta, código…': 'link, deal, code…', 'boquillas 0.4, PEI, IPA…': '0.4 nozzles, PEI, IPA…', '¿Qué hay que comprar?': 'What needs buying?',
    '¿qué hay que comprar?': 'what needs buying?', '¿Cómo lo apuntas?': 'How do you want to record it?', 'Dar de alta las bobinas': 'Add the spools to stock',
    'rellena «Añadir bobinas»': 'fills in “Add spools”', 'Solo marcar como comprado': 'Just mark as bought', 'sin tocar el almacén': 'without touching stock',
    'ya no hace falta': 'no longer needed', 'Lista copiada': 'List copied', 'La lista está vacía': 'The list is empty', 'Sin proveedor': 'No supplier',
    'Dando de alta la compra de': 'Adding the purchase of', ': revisa marca y color y pulsa «Añadir al almacén».': ': check brand and colour and press “Add to stock”.',
    'no llega para los pedidos': 'not enough for the orders', 'Proveedor': 'Supplier', 'Amazon, tienda de la marca…': 'Amazon, brand store…',
    'Actualizar el precio del material': 'Update the material price', 'Precios': 'Prices', 'Más barato': 'Cheapest', 'Media': 'Average', 'Más caro': 'Most expensive',
    'Mejor precio por proveedor:': 'Best price per supplier:', 'Pagado': 'Paid',
    'Todavía no hay compras con precio. Se apuntan solas al añadir bobinas o registrar una entrada con lo pagado.': 'No priced purchases yet. They are recorded automatically when you add spools or log stock in with the amount paid.',
    'Gastos fijos': 'Fixed expenses', '+ Nuevo gasto fijo': '+ New fixed expense', 'al mes': 'a month', 'Cada': 'Every', 'Próximo': 'Next', 'Apuntado': 'Booked',
    'Cuota de autónomo, dominio, alquiler, suscripciones… Se apuntan solos como gasto el día que toca, sin duplicarse.': 'Self-employed fee, domain, rent, subscriptions… They are booked as expenses on the right day, never twice.',
    'No hay gastos fijos. Añade la cuota de autónomo, el dominio, el alquiler…': 'No fixed expenses. Add the self-employed fee, domain, rent…',
    'Cada mes': 'Every month', 'Cada 3 meses': 'Every 3 months', 'Cada 6 meses': 'Every 6 months', 'Cada año': 'Every year', 'terminado': 'finished', 'en pausa': 'paused',
    'Reanudar': 'Resume', 'Editar gasto fijo': 'Edit fixed expense', 'Cuota de autónomo, dominio, alquiler…': 'Self-employed fee, domain, rent…',
    'Importe (€)': 'Amount (€)', 'Cada cuánto': 'How often', 'Día del mes': 'Day of month', 'Del 1 al 28.': 'From 1 to 28.', 'Desde (mes)': 'From (month)',
    'Hasta (opcional)': 'Until (optional)', '¿Quién lo paga?': 'Who pays?', 'AAAA-MM': 'YYYY-MM',
    'Si el inicio es un mes pasado, se apuntan también los meses que faltan hasta hoy.': 'If the start is a past month, the missing months up to today are booked too.',
    '¿Borrar este gasto fijo?': 'Delete this fixed expense?', 'Borrar y conservar lo ya apuntado': 'Delete and keep what was booked',
    'los movimientos se quedan en contabilidad': 'the entries stay in accounting', 'Borrar también lo apuntado': 'Also delete what was booked',
    'quita sus movimientos': 'removes its entries', 'Borrado': 'Deleted', 'pon el concepto (p. ej. Cuota de autónomo)': 'enter a description (e.g. self-employed fee)',
    'pon el importe': 'enter the amount', 'mes de inicio no válido (AAAA-MM)': 'invalid start month (YYYY-MM)',
    'Apuntar fallo': 'Log failure', '¿A qué porcentaje iba cuando falló? (1-100)': 'What percentage was it at when it failed? (1-100)',
    '¿Qué pasó? (opcional)': 'What happened? (optional)', 'despegue, espagueti, atasco, corte de luz…': 'detached, spaghetti, clog, power cut…',
    'despegue, espagueti, atasco…': 'detached, spaghetti, clog…', '¿Qué pieza era?': 'Which piece was it?', 'Porcentaje al que se paró': 'Percentage where it stopped',
    'Imprimir etiquetas': 'Print labels', '¿Imprimir las etiquetas con QR de estas bobinas?': 'Print QR labels for these spools?',
    'Pesar bobina': 'Weigh spool', '¿Cuánto pesa ahora la bobina entera? (g)': 'How much does the whole spool weigh now? (g)', 'Guardar peso': 'Save weight',
    'Suele ser 150-250 g. Lo recordaré para esa marca.': 'Usually 150-250 g. I will remember it for that brand.', 'Editar bobina': 'Edit spool',
    'Nombre del color': 'Colour name', 'estantería, caja seca…': 'shelf, dry box…',
    '¿Borrar la bobina del almacén? Si solo se ha gastado, mejor «Marcar como gastada» para conservar el historial.': 'Delete the spool from stock? If it is just used up, better “Mark as used up” to keep the history.',
    'Entrada de material': 'Stock in', 'Pagado en total (€)': 'Total paid (€)', 'Vacío = no apuntar el gasto en contabilidad.': 'Empty = do not book the expense.',
    '¿Quién lo pagó?': 'Who paid?', 'Registrar entrada': 'Record stock in', 'Pesa las bobinas sin el carrete.': 'Weigh the filament without the spool.',
    'Ajustar': 'Adjust', 'Ninguno': 'None', 'Cantidad': 'Quantity', '¿Seguro?': 'Sure?', 'Imprimir ya': 'Print now', 'Enviar': 'Send', 'Empezar a imprimir ya': 'Start printing now',
    'Sin marcar: solo se sube y lo arrancas tú desde la impresora.': 'Unchecked: it is only uploaded and you start it on the printer.',
    'Nueva contraseña (mín. 8)': 'New password (min. 8)', 'Cambiar': 'Change', '¿Cuántas unidades quieres fabricar para tener en stock?': 'How many units do you want to make for stock?',
    'Crear pedido': 'Create order', 'Nombre del conjunto': 'Kit name', 'Nuevo conjunto': 'New kit', 'p. ej. Granada de airsoft M67': 'e.g. Airsoft grenade M67',
    'Recalcular precios': 'Recalculate prices', 'Recalcular': 'Recalculate', 'Precios cambiados': 'Prices changed',
    'Recalcula precio y coste de todos los productos con los ajustes actuales (margen, luz, materiales…).': 'Recalculates price and cost of every product with the current settings (margin, electricity, materials…).',
    'Tu contraseña': 'Your password', 'Volver a la versión anterior': 'Go back to the previous version', 'Volver atrás': 'Roll back', '¿Qué chat?': 'Which chat?',
    'Tarea hecha': 'Task done', '¿Alguna nota? (opcional)': 'Any notes? (optional)', 'qué has cambiado, qué grasa…': 'what you changed, which grease…', 'Marcar hecha': 'Mark done',
    'Cargar tareas de mantenimiento': 'Load maintenance tasks', '¿Cuándo le hiciste mantenimiento por última vez?': 'When did you last service it?', 'Vacío = hoy.': 'Empty = today.',
    'Sustituir las tareas que ya tiene': 'Replace its current tasks', 'Sin marcar: solo se añaden las que falten.': 'Unchecked: only missing ones are added.', 'Cargar': 'Load',
    'Sumar horas': 'Add hours', 'Horas a sumar': 'Hours to add', 'Sumar': 'Add',
    'Lo que ya llevaba la impresora antes de usar MiTallercito, o impresiones sin pedido. Negativo para restar.': 'What the printer already had before MiTallercito, or prints without an order. Negative to subtract.',
    'Venta libre': 'Custom sale', '¿Qué es?': 'What is it?', 'Precio (€)': 'Price (€)', 'Nuevo puesto': 'New stall', 'p. ej. Mercadillo medieval de Toledo': 'e.g. Medieval fair in Toledo',
    'Lugar (opcional)': 'Place (optional)', 'Coste del puesto (€)': 'Stall cost (€)', 'Cambio inicial en caja (€)': 'Starting cash float (€)', 'Abrir puesto': 'Open stall',
    'Editar puesto': 'Edit stall', 'Cambio inicial (€)': 'Cash float (€)', 'Cerrar puesto': 'Close stall', '¿Cuánto efectivo hay? (€)': 'How much cash is there? (€)',
    'Añadir varias variantes': 'Add several variants', 'Variantes separadas por comas': 'Variants separated by commas', 'Negro, Blanco, Rojo': 'Black, White, Red',
    'Repetir pedido': 'Repeat order', 'Repetir': 'Repeat', '¿Guardar sin archivo?': 'Save without a file?', 'Guardar sin archivo': 'Save without a file',
    'Se creará un pedido nuevo (recibido) con las mismas piezas, fichas de impresión y archivos.': 'A new order (received) will be created with the same pieces, print sheets and files.',
    'Este pedido no tiene STL ni 3MF adjunto. Si algún día quieres repetirlo igual, te hará falta.': 'This order has no STL or 3MF attached. You will need it if you ever want to repeat it.',
    'Deshacer': 'Undo', '(Conexión: Moonraker, OctoPrint o PrusaLink + IP).': '(Connection: Moonraker, OctoPrint or PrusaLink + IP).',
    '¿Prefieres otro precio? Tu precio por pieza': 'Prefer another price? Your price per piece', '¿Prefieres otro precio? Tu precio por pieza (con IVA)': 'Prefer another price? Your price per piece (incl. VAT)',
    '¿Prefieres otro precio? Tu precio por pieza (sin IVA)': 'Prefer another price? Your price per piece (excl. VAT)', 'déjalo vacío para usar el calculado': 'leave empty to use the calculated one',
    'Usar el calculado': 'Use the calculated one', 'Para no perder dinero, como mínimo': 'To not lose money, at least', 'por pieza.': 'per piece.', 'ganas (total)': 'you earn (total)',
    'pierdes (total)': 'you lose (total)', 'por pieza': 'per piece', 'sobre el coste': 'on cost', 'Cobras en total': 'You charge in total', 'IVA a ingresar': 'VAT to pay',
    'Comisión plataforma': 'Platform fee', 'Te cuesta': 'It costs you', 'Mínimo para no perder': 'Break-even price', 'Con este precio pierdes dinero.': 'At this price you lose money.',
    'Al guardar en el catálogo o añadir al pedido se usa tu precio.': 'Saving to the catalog or adding to an order uses your price.',
    'Ajuste de inventario': 'Stock adjustment',
    '＋ Nuevo material…': '＋ New material…', 'Nombre del material nuevo': 'New material name', 'PLA negro, PETG Sunlu…': 'Black PLA, Sunlu PETG…',
    'Se crea al añadir la bobina. Su precio sale de lo pagado; si lo dejas vacío, se usa uno estándar que puedes cambiar en Ajustes.': 'It is created when you add the spool. Its price comes from what you paid; if empty, a standard one is used that you can change in Settings.',
    'Ponle nombre al material nuevo': 'Name the new material', 'ponle nombre al material nuevo': 'name the new material',
    'Pegar de Amazon o de la tienda': 'Paste from Amazon or the shop', 'Enlace o título del producto': 'Product link or title', 'Leer': 'Read', 'Leyendo…': 'Reading…',
    'No he reconocido nada: rellénalo a mano.': 'Nothing recognised: fill it in by hand.', 'Revisa el formulario y pulsa «Añadir al almacén».': 'Check the form and press “Add to stock”.',
    'Añadir una bobina de cada color': 'Add one spool of each colour', 'o revisa el formulario para añadirlas iguales': 'or check the form to add them all the same',
    'Una de cada color': 'One of each colour', 'tipo': 'type', 'color': 'colour', 'peso': 'weight',
    'pega el enlace o el título del producto': 'paste the product link or title',
    'Solo leo enlaces de Amazon y AliExpress; con otras tiendas pega el título.': 'I only read Amazon and AliExpress links; for other shops paste the title.',
    'La tienda no ha dejado leer la ficha (pide captcha): lo saco del enlace. Si falta algo, pega el título.': 'The shop did not let me read the page (captcha): I took it from the link. If something is missing, paste the title.',
    // --- 1.0: organización de casa
    'Filamento': 'Filament', 'Componentes': 'Components', 'Terminado': 'Finished', 'Ubicaciones': 'Locations', 'Compra': 'Shopping',
    'Componentes y ferretería': 'Components and hardware', 'Modo recuento': 'Count mode', '+ Nuevo componente': '+ New component', 'Nuevo componente': 'New component',
    'Muelles, tornillos, insertos, imanes, rodamientos, cajas, bolsas, pintura… Su coste por unidad sale del pack, y al llegar al mínimo pasan solos a la lista de la compra. Se gastan solos en los pedidos según la receta de cada artículo.':
      'Springs, screws, inserts, magnets, bearings, boxes, bags, paint… The unit cost comes from the pack, and when they hit the minimum they go to the shopping list. Orders use them up automatically following each item’s recipe.',
    'Buscar…': 'Search…', 'Todas las categorías': 'All categories', 'Solo los que faltan': 'Only what is missing', 'Componente': 'Component', 'Hay': 'In stock',
    'Mínimo': 'Minimum', '€/ud': '€/unit', 'Dónde': 'Where', 'Va en': 'Used in', '+ Entrada': '+ Stock in', 'falta': 'low', 'comprar': 'buy',
    'Nada con ese filtro.': 'Nothing matches that filter.', 'Aún no hay componentes. Añade los muelles, tornillos, imanes… que uses.': 'No components yet. Add the springs, screws, magnets… you use.',
    'Editar componente': 'Edit component', 'Pegar de Amazon o de la tienda (opcional)': 'Paste from Amazon or the shop (optional)',
    'Enlace o título: rellena nombre, precio y unidades del pack': 'Link or title: fills in name, price and pack size',
    'Tornillo M3×10 DIN912, Muelle 0,8×6×20, Imán 6×2…': 'Screw M3×10 DIN912, Spring 0.8×6×20, Magnet 6×2…', 'Tornillería, Muelles, Imanes…': 'Screws, Springs, Magnets…',
    'Se cuenta en': 'Counted in', 'unidades': 'units', 'pares': 'pairs', 'metros': 'metres', 'centímetros': 'centimetres', 'mililitros': 'millilitres', 'gramos': 'grams',
    'Cuántos trae el pack': 'Pack size', 'Precio del pack (€)': 'Pack price (€)', 'El coste por unidad sale solo.': 'The unit cost is worked out for you.',
    'Cuántos tienes ahora': 'How many you have now', 'Avisar cuando queden': 'Alert when down to', '0 = sin aviso': '0 = no alert', 'Dónde está': 'Where it is',
    'Enlace de compra': 'Buy link', 'En uso (desmárcalo para ocultarlo sin perder el historial)': 'In use (untick to hide it without losing its history)',
    'No he sacado el nombre: escríbelo a mano': 'Could not get the name: type it in', 'Ponle nombre al componente': 'Name the component', 'ponle nombre al componente': 'name the component',
    'Las recetas que lo usan conservan el nombre y el coste, pero dejará de descontarse.': 'Recipes using it keep the name and cost, but it will no longer be deducted.',
    'o unidades sueltas': 'or loose units', 'Vacío = no apuntar el gasto.': 'Empty = do not book the expense.', 'Recontado': 'Recounted', 'Pon un número': 'Enter a number',
    'Sumar al almacén': 'Add to stock', 'Sumado al almacén': 'Added to stock', 'Sumarlo al almacén': 'Add it to stock', 'componente': 'component',
    '¿cuántos han entrado?': 'how many came in?', 'pon cuántos hay': 'enter how many there are', '¿cuántos has usado?': 'how many did you use?', 'modo no válido': 'invalid mode',
    'ese componente no existe': 'that component does not exist', 'ese sitio no existe': 'that place does not exist', 'ponle nombre': 'give it a name',
    'no puede ir dentro de sí misma': 'it cannot be inside itself',
    'Ubicaciones': 'Locations', 'Etiquetas QR': 'QR labels', '+ Nueva ubicación': '+ New location', 'Nueva ubicación': 'New location', 'Editar ubicación': 'Edit location',
    'Estanterías, cajoneras, cajas… unas dentro de otras. Pega su etiqueta QR: al escanearla con el móvil ves qué hay dentro y puedes recontar en el momento.':
      'Shelves, drawer units, boxes… one inside another. Stick on its QR label: scan it with your phone to see what is inside and recount on the spot.',
    'Aún no hay ubicaciones. Empieza por lo grande (la estantería) y mete dentro cajas y cajones.': 'No locations yet. Start with the big one (the shelf) and put boxes and drawers inside.',
    '+ dentro': '+ inside', 'Añadir dentro': 'Add inside', 'Estantería': 'Shelf', 'Cajonera': 'Drawer unit', 'Cajón': 'Drawer', 'Caja': 'Box', 'Armario': 'Cabinet', 'Balda': 'Shelf board', 'Otro': 'Other',
    'Estantería del taller, Caja tornillería, Cajón 3…': 'Workshop shelf, Screw box, Drawer 3…', 'Está dentro de': 'Inside', '— nada (es lo más grande) —': '— nothing (it is the biggest) —',
    '— sin ubicación —': '— no location —', 'Lo que haya dentro pasa al sitio que la contiene.': 'Whatever is inside moves to the place that contains it.', 'Borrada': 'Deleted',
    'Bobinas': 'Spools', 'Producto terminado': 'Finished goods', 'Vacía. Asigna aquí componentes, bobinas o artículos desde su ficha.': 'Empty. Assign components, spools or items here from their page.',
    'Cerrar': 'Close', 'uds': 'pcs', 'Crea ubicaciones con QR en Almacén → Ubicaciones.': 'Create locations with QR in Stock → Locations.',
    'Para reponer': 'To restock', 'Todo en orden: nada por debajo del mínimo.': 'All good: nothing below the minimum.', '¿Qué me falta?': 'What am I missing?',
    'Lo que tienes hecho y dónde. Con un': 'What you have made and where. With a', 'mínimo': 'minimum',
    ', la app te avisa cuando toca fabricar más. Cambia la cantidad para recontar.': ', the app tells you when to make more. Change the amount to recount.',
    'Artículo': 'Item', 'conjunto': 'kit', 'Vacío = bajo pedido': 'Empty = made to order', 'Aún no hay artículos en el catálogo.': 'No items in the catalog yet.',
    'Unidades': 'Units', 'Variante': 'Variant', 'Añadir lo que falta a la compra': 'Add what is missing to the shopping list', 'Fabricar': 'Make',
    'Piezas a imprimir': 'Pieces to print', 'Filamento / resina': 'Filament / resin', 'Por unidad': 'Per unit', 'Hace falta': 'Needed', 'Tienes': 'You have', 'Falta': 'Missing',
    'sin controlar': 'not tracked', 'No falta nada': 'Nothing missing', 'Fabricar igual': 'Make anyway',
    'Falta algo de lo que pide la receta. ¿Crear igualmente el pedido de fabricación?': 'Something the recipe needs is missing. Create the production order anyway?',
    'Este artículo no tiene receta: añade su cálculo (material) y sus componentes en el catálogo.': 'This item has no recipe: add its calculation (material) and components in the catalog.',
    '¿Qué artículo?': 'Which item?', '¿Qué me falta para fabricar…?': 'What am I missing to make…?', 'Recontar componentes': 'Recount components',
    'Taller': 'Workshop', 'Componentes que faltan': 'Components running low', 'a la compra': 'to the list',
    'Receta': 'Recipe', 'Piezas impresas': 'Printed pieces', 'Componentes y material extra': 'Components and extra material',
    '— muelles, tornillos, imanes, pintura… por unidad': '— springs, screws, magnets, paint… per unit', '+ componente': '+ component', 'Por ud.': 'Per unit',
    'Elige de tus componentes o escribe': 'Pick one of your components or type', 'Lo marca el componente': 'Set by the component',
    'no está en el almacén: no se descuenta': 'not in stock: it is not deducted', 'Componentes:': 'Components:',
    'por unidad (se suman al coste al guardar; el precio, con «Recalcular todos los precios»)': 'per unit (added to the cost on save; to the price, with “Recalculate all prices”)',
    'Pasos de montaje (pintura, consejos…)': 'Assembly steps (paint, tips…)', '1. Pon los insertos con el soldador a 220 °C…': '1. Push in the inserts with the iron at 220 °C…',
    'Las fotos de los pasos súbelas en «Archivos del modelo»: se ven aquí debajo y van en el .zip.': 'Upload step photos in “Model files”: they show below and go in the .zip.',
    'Stock mínimo (avisa para reponer)': 'Minimum stock (restock alert)', 'Dónde se guarda': 'Where it is kept', 'Componentes': 'Components', 'Ubicaciones': 'Locations',
    'Recuento': 'Recount', 'Stock inicial': 'Initial stock', 'Uso': 'Use',
    'Producto (del catálogo o lo que quieras)': 'Product (from the catalog or anything you like)',
    'Descripción libre: sale en el presupuesto y el albarán (opcional)': 'Free description: shown on the quote and delivery note (optional)',
  };
  const MONTHS = {enero: 'January', febrero: 'February', marzo: 'March', abril: 'April', mayo: 'May', junio: 'June', julio: 'July', agosto: 'August',
    septiembre: 'September', octubre: 'October', noviembre: 'November', diciembre: 'December',
    ene: 'Jan', feb: 'Feb', mar: 'Mar', abr: 'Apr', may: 'May', jun: 'Jun', jul: 'Jul', ago: 'Aug', sep: 'Sep', oct: 'Oct', nov: 'Nov', dic: 'Dec'};
  const tr = s => EN[s] ?? s, mo = m => MONTHS[m] || m;
  const RULES = [
    [/^\(ya tienes (\d+) hechos\)$/, (_, n) => `(you already have ${n} made)`], [/^Ahora: (.+) por unidad$/, (_, v) => `Now: ${v} per unit`],
    [/^(Estantería|Cajonera|Cajón|Caja|Armario|Balda|Otro) · (.+)$/, (_, k, r) => `${tr(k)} · ${r.replace(/comp\./, 'comp.').replace(/bob\./, 'spools').replace(/art\./, 'items')}`],
    [/^Fabricar (\d+)$/, (_, n) => `Make ${n}`], [/^hay (\d+) de (\d+)$/, (_, a, b) => `${a} of ${b}`], [/^hay (\d+), mínimo (\d+)(, (\d+) en marcha)?$/, (_, a, b, _c, d) => `${a} in stock, minimum ${b}${d ? `, ${d} in progress` : ''}`],
    [/^Piezas (.+) · componentes (.+) · coste total$/, (_, a, b) => `Pieces ${a} · components ${b} · total cost`],
    [/^¿Cuántos packs de (.+)\?$/, (_, q) => `How many packs of ${q}?`], [/^Te falta algo para hacer (\d+)\.$/, (_, n) => `Something is missing to make ${n}.`],
    [/^✓ Tienes todo lo controlado para hacer (\d+)\.$/, (_, n) => `✓ You have everything tracked to make ${n}.`], [/^Entrada: (.+)$/, (_, c) => `Stock in: ${c}`],
    [/^Comprado: (.+)$/, (_, c) => `Bought: ${c}`], [/^¿Qué me falta\? · (.+)$/, (_, p) => `What am I missing? · ${p}`], [/^¿Borrar «(.+)»\?$/, (_, x) => `Delete “${x}”?`],
    [/^A la compra: (.+)$/, (_, x) => `Added to the list: ${x}`], [/^quedan ([\d.,]+) (.+)$/, (_, n, u) => `${n} ${tr(u)} left`],
    [/^Sin controlar en el almacén: (.+)\. Enlázalos a un componente en la receta para que se cuenten\.$/, (_, x) => `Not tracked in stock: ${x}. Link them to a component in the recipe so they are counted.`],
    [/^✓ del almacén · hay (.+)$/, (_, r) => `✓ in stock · ${r.replace(' · 📍', ' · 📍')} available`], [/^Pedido #(\d+) creado: al pasar a «listo» se suman (\d+) al stock$/, (_, o, n) => `Order #${o} created: when it is “ready”, ${n} are added to stock`],
    [/^Para (\d+) × (.+)$/, (_, n, p) => `For ${n} × ${p}`],
    [/^Revisa: no he encontrado (.+)\.$/, (_, l) => `Check: I did not find ${l.split(', ').map(x=>tr(x)).join(', ')}.`], [/^Son (\d+) colores:$/, (_, n) => `${n} colours:`],
    [/^No he podido abrir la ficha \((.+)\): lo saco del enlace\. Si falta algo, pega el título\.$/, (_, e) => `Could not open the page (${e}): I took it from the link. If something is missing, paste the title.`],
    [/^Añadir (\d+)$/, (_, n) => `Add ${n}`],
    [/^Se añadirán (\d+) bobinas de (.+): (.+)\.(?: Lo pagado \((.+)\) se reparte entre ellas\.)?$/, (_, n, b, c, p) => `${n} spools of ${b} will be added: ${c}.${p ? ` What you paid (${p}) is split between them.` : ''}`],
    [/^\(([\d.,]+ €|€[\d.,]+) sin IVA\)$/, (_, v) => `(${v} excl. VAT)`], [/^Frente al calculado \((.+)\)$/, (_, v) => `Versus calculated (${v})`], [/^(.+) \/ pieza$/, (_, v) => `${v} / piece`],
    [/^\(día (\d+)\)$/, (_, d) => `(day ${d})`], [/^se acaba en (\d+) días$/, (_, d) => `runs out in ${d} days`], [/^~(.+)\/ud$/, (_, v) => `~${v}/unit`],
    [/^Precios: (.+)$/, (_, m) => `Prices: ${m}`], [/^(.+) · últimos movimientos$/, (_, m) => `${m} · latest movements`],
    [/^Contraseña de (.+)$/, (_, u) => `Password for ${u}`], [/^Ajustar stock: (.+)$/, (_, m) => `Adjust stock: ${m}`],
    [/^¿Cuántos envases de (.+)\?$/, (_, q) => `How many packs of ${q}?`], [/^¿Cuánto queda de verdad\? \((.+)\)$/, (_, u) => `How much is really left? (${u})`],
    [/^Peso de la bobina vacía de (.+) \(g\)$/, (_, b) => `Empty spool weight for ${b === 'esta marca' ? 'this brand' : b} (g)`],
    [/^Ha fallado: (.+)$/, (_, p) => `Failed: ${p}`], [/^Enviar a (.+)$/, (_, p) => `Send to ${p}`],
    [/^(.+) empezará a imprimir ahora\. Comprueba que la cama está libre y el filamento cargado\.$/, (_, p) => `${p} will start printing now. Check the bed is clear and filament is loaded.`],
    [/^Cuenta la caja\. Debería haber (.+)\.$/, (_, v) => `Count the cash. There should be ${v}.`],
    [/^Guardado · (\d+) gasto\(s\) apuntado\(s\)$/, (_, n) => `Saved · ${n} expense(s) booked`], [/^Nada con «(.*)»\.$/, (_, q) => `Nothing for “${q}”.`],
    [/^Bobina #(\d+) · (.+)$/, (_, n, r) => `Spool #${n} · ${r}`], [/^Pedido #(\d+) · (.+)$/, (_, n, r) => `Order #${n} · ${r}`],
    [/^(\d+) bobina\(s\)$/, (_, n) => `${n} spool(s)`], [/^(\d+) bobina\(s\) añadida\(s\)$/, (_, n) => `${n} spool(s) added`],
    [/^Quedan (.+)$/, (_, v) => `${v} left`], [/^⏰ (.+) en (.+)$/, (_, a, b) => `⏰ ${a} in ${tr(b)}`],
    [/^Piezas (.+) · material extra (.+) · coste total$/, (_, a, b) => `Pieces ${a} · extra parts ${b} · total cost`],
    [/^Perdido en fallos: (.+) \(ya restado del beneficio\)$/, (_, v) => `Lost to failures: ${v} (already taken off the profit)`],
    [/^(.*) · coste laminador$/, (_, a) => `${a} · slicer cost`], [/^❌ (.+) al$/, (_, a) => `❌ ${a} at`],
    [/^«(.+)»: ¿a qué porcentaje iba la impresión cuando falló\? \(1-100\)$/, (_, a) => `“${a}”: what percentage was the print at when it failed? (1-100)`],
    [/^(.+) iba al (.+)%\. ¿Qué pieza era\?$/, (_, p, v) => `${p} was at ${v}%. Which piece was it?`],
    [/^No sé lo que pesa vacía una bobina de (.+)\. ¿Cuánto pesa la bobina vacía \(g\)\? \(suele ser 150-250 g\)$/, (_, b) => `I don’t know the empty spool weight for ${b}. How much does the empty spool weigh (g)? (usually 150-250 g)`],
    [/^Bobina vacía de (.+) \((.+)\): (.+) g, la sabemos de (\d+) pesada\(s\)\.$/, (_, b, k, g, n) => `Empty ${b} spool (${k}): ${g} g, known from ${n} weighing(s).`],
    [/^Aún no sabemos lo que pesa vacía una bobina de esta marca: pésala cuando se acabe\.$/, () => 'We don’t know the empty spool weight for this brand yet: weigh it when it runs out.'],
    [/^Última revisión: hace (\d+) min\.$/, (_, n) => `Last check: ${n} min ago.`],
    [/^⚠ La última revisión fue hace (\d+) min: el temporizador de avisos no está funcionando\.$/, (_, n) => `⚠ The last check was ${n} min ago: the alerts timer is not running.`],
    [/^⚠ Aún no se ha revisado ninguna vez\. .*$/, () => '⚠ Not checked yet. If it stays like this after 15 minutes, update from the Proxmox host (it creates the alerts timer).'],
    [/^No se pudo: (.+)$/, (_, e) => `Could not: ${tr(e)}`], [/^Chat: (.+)$/, (_, c) => `Chat: ${c}`],
    [/^(.+) — (lo tienes|algo parecido|no lo tienes)$/, (_, a, b) => `${a} — ${tr(b)}`],
    [/^quedan de (.+)$/, (_, v) => `left of ${v}`],
    [/^(\d+) por (.+) €$/, (_, n, v) => `${n} for €${v}`], [/^la (\d+)ª al (.+) %$/, (_, n, v) => `unit ${n} at ${v}%`], [/^la (\d+)ª gratis$/, (_, n) => `unit ${n} free`],
    [/^(.+) \((\d+) por (.+) €\)$/, (_, a, n, v) => `${a} (${n} for €${v})`], [/^(.+) \(la (\d+)ª al (.+) %\)$/, (_, a, n, v) => `${a} (unit ${n} at ${v}%)`],
    [/^Oferta: (.+)$/, (_, x) => 'Offer: ' + tr(x)], [/^categoría (.+)$/, (_, c) => `category ${c}`],
    [/^Ejemplo: (.+) unidades por (.+) €\. Se juntan de la más cara a la más barata\.$/, (_, n, v) => `Example: ${n} units for €${v}. Units are grouped from most to least expensive.`],
    [/^Ejemplo: de cada (.+), la más barata con un (.+) % de descuento\.$/, (_, n, v) => `Example: in every ${n}, the cheapest gets ${v}% off.`],
    [/^Ejemplo: un (.+) % menos en todo lo que entre\.$/, (_, v) => `Example: ${v}% off everything included.`],
    [/^ritmo de los últimos (\d+) días · compra en (\d+) días$/, (_, a, b) => `rate over the last ${a} days · purchases take ${b} days`],
    [/^faltan (.+) para los pedidos$/, (_, v) => `${v} short for orders`], [/^se acaba hacia el (.+)$/, (_, d) => `runs out around ${d}`], [/^comprar (\d+)$/, (_, n) => `buy ${n}`],
    [/^(\d+) variantes · $/, (_, n) => `${n} variants · `], [/^(\d+) archivo\(s\) traído\(s\) de Manyfold$/, (_, n) => `${n} file(s) fetched from Manyfold`],
    [/^Ofertas aplicadas: −(.+)$/, (_, v) => `Offers applied: −${v}`], [/^(\d+) en total: afina la búsqueda\.$/, (_, n) => `${n} in total: narrow your search.`],
    [/^✓ Conectado: (\d+) modelo\(s\) \(con credenciales\)$/, (_, n) => `✓ Connected: ${n} model(s) (with credentials)`], [/^✓ Conectado: (\d+) modelo\(s\) \(solo públicos\)$/, (_, n) => `✓ Connected: ${n} model(s) (public only)`],
    [/^¿Cuántas unidades de «(.+)» quieres fabricar para tener en stock\?$/, (_, n) => `How many “${n}” do you want to make for stock?`],
    [/^cada (.+)$/, (_, x) => 'every ' + x.replace(/impresiones/g, 'prints').replace(/días/g, 'days')],
    [/^(\d+(?:[.,]\d+)?) impresiones$/, (_, n) => `${n} prints`], [/^(.+) h · (\d+) impresiones$/, (_, h, n) => `${h} h · ${n} prints`],
    [/^(\d+) venta\(s\)$/, (_, n) => `${n} sale(s)`], [/^Cobrar (.+)$/, (_, v) => `Charge ${v}`], [/^Cobrar (.+) ↓$/, (_, v) => `Charge ${v} ↓`],
    [/^Vendido: (.+)$/, (_, v) => `Sold: ${v}`], [/^quedan (\d+)$/, (_, n) => `${n} left`], [/^\(stock (\d+)\)$/, (_, n) => `(stock ${n})`],
    [/^: (.+)$/, (_, x) => ': ' + tr(x)],
    [/^Pedido #(\d+) - (.+?) \((efectivo|tarjeta|bizum|transferencia|otro)\)$/, (_, n, c, m) => `Order #${n} - ${tr(c)} (${tr(m.charAt(0).toUpperCase() + m.slice(1))})`],
    [/^Coste de lo vendido (.+) · puesto (.+) · cambio inicial (.+)$/, (_, a, b, c) => `Cost of goods sold ${a} · stall ${b} · starting change ${c}`],
    [/^Caja contada: $/, () => 'Counted cash: '], [/^\((sobran|faltan) (.+)\)$/, (_, k, v) => `(${k === 'sobran' ? 'over' : 'short'} by ${v})`],
    [/^Puesto: (.+)$/, (_, n) => `Stall: ${n}`], [/^Nueva tarea · (.+)$/, (_, n) => `New task · ${n}`], [/^Mantenimiento de (.+)$/, (_, n) => `Maintenance of ${n}`],
    [/^Cuenta la caja\. Debería haber (.+) en efectivo\. ¿Cuánto hay\?$/, (_, v) => `Count the cash. There should be ${v} in cash. How much is there?`],
    [/^¿Cuántas unidades de «(.+)» quieres fabricar para tener en stock\?$/, (_, n) => `How many “${n}” do you want to make for stock?`],
    [/^Pedido #(\d+) creado: al pasar a «listo» se suman (\d+) al stock$/, (_, o, n) => `Order #${o} created: ${n} will be added to stock when it is “ready”`],
    [/^(\d+) línea\(s\) se metieron a mano sin calculadora: cuentan en facturado y coste, pero no en luz, material ni horas\.$/, (_, n) => `${n} line(s) were entered by hand without the calculator: they count towards revenue and cost, but not electricity, material or hours.`],
    [/^hace (\d+) d$/, (_, n) => `${n} d overdue`], [/^en (\d+) d$/, (_, n) => `in ${n} d`],
    [/^(\d+) con la entrega pasada$/, (_, n) => `${n} overdue`], [/^(\d+) este mes$/, (_, n) => `${n} this month`],
    [/^(\d+) pedido\(s\) entregados o listos$/, (_, n) => `${n} order(s) delivered or ready`],
    [/^(\S+) (\d{4}) · (\d+) pedido\(s\) nuevo\(s\) esta semana$/, (_, m, y, n) => `${mo(m)} ${y} · ${n} new order(s) this week`],
    [/^(Buenos días|Buenas tardes|Buenas noches), (.+)$/, (_, g, u) => `${{'Buenos días': 'Good morning', 'Buenas tardes': 'Good afternoon', 'Buenas noches': 'Good evening'}[g]}, ${u}`],
    [/^lo lleva (.+)$/, (_, u) => `handled by ${u}`], [/^gastos (.+)$/, (_, v) => `expenses ${v}`], [/^ing (.+) · gas (.+)$/, (_, a, b) => `inc ${a} · exp ${b}`],
    [/^Detalle de (\S+) (\d{4})$/, (_, m, y) => `Details for ${mo(m)} ${y}`], [/^Luz estimada: (.+)$/, (_, v) => `Estimated electricity: ${v}`],
    [/^\((.+) kWh · (.+) h de máquina\)$/, (_, a, b) => `(${a} kWh · ${b} h machine time)`],
    [/^(Facturado|Luz estimada|kWh|Beneficio) · (\d{4})$/, (_, k, y) => `${k === 'Luz estimada' ? 'Estimated electricity' : tr(k)} · ${y}`],
    [/^Coste total \((\d+) pz · (.+) h\)$/, (_, a, b) => `Total cost (${a} pcs · ${b} h)`], [/^Precio total \((\d+) piezas\)$/, (_, n) => `Total price (${n} pieces)`],
    [/^Pedido #(\d+)$/, (_, n) => `Order #${n}`], [/^Creado el pedido #(\d+)$/, (_, n) => `Order #${n} created`], [/^Placa (\d+)$/, (_, n) => `Plate ${n}`],
    [/^Placa (\d+): (.+)$/, (_, n, r) => `Plate ${n}: ${r}`], [/^Último: (.+)$/, (_, f) => `Last: ${f}`],
    [/^quedan (.+) · fin (.+)$/, (_, a, b) => `${a} left · ends ${b}`], [/^(\d+) h (\d+) min$/, (_, h, m) => `${h} h ${m} min`],
    [/^de (.+): con tu margen saldría a$/, (_, v) => `of ${v} applies: with your margin it would be`],
    [/^\(redondeo «(.+)»\)\. Cambios pequeños de margen pueden dar el mismo precio\.$/, (_, r) => `(rounding “${tr(r)}”). Small margin changes can give the same price.`],
    [/^Apuntado: (.+) de luz$/, (_, v) => `Booked: ${v} of electricity`], [/^Instalando (.+)…$/, (_, v) => `Installing ${v}…`],
    [/^Actualizado a (.+), recargando…$/, (_, v) => `Updated to ${v}, reloading…`], [/^(\d+) precio\(s\) cambiado\(s\)$/, (_, n) => `${n} price(s) changed`],
    [/^quedan (.+)$/, (_, v) => `${v} left`], [/^⚠️ (.+) — quedan$/, (_, m) => `⚠️ ${m} — left`], [/^Asignada al pedido #(\d+)$/, (_, n) => `Assigned to order #${n}`],
    [/^Sin conexión: (.+)$/, (_, e) => `Offline: ${tr(e)}`], [/^Historial de (.+)$/, (_, p) => `History of ${p}`],
    [/^Conectada ✓ (.*)$/, (_, r) => `Connected ✓ ${r}`], [/^No conecta: (.+)$/, (_, e) => `Cannot connect: ${tr(e)}`],
    [/^Pedido #(\d+) - (.+)$/, (_, n, c) => `Order #${n} - ${c}`], [/^Para repartir a medias: (.+) debe pasar (.+) a (.+)\.$/, (_, a, v, b) => `To split evenly: ${a} owes ${v} to ${b}.`],
    [/^demasiados intentos, espera (\d+) min$/, (_, n) => `too many attempts, wait ${n} min`], [/^mínimo (\d+) caracteres$/, (_, n) => `minimum ${n} characters`],
    [/^contraseña de mínimo (\d+) caracteres$/, (_, n) => `password must be at least ${n} characters`],
    [/^(.+) está ocupada \((.+)\)\. Se puede subir sin arrancar\.$/, (_, p, s) => `${p} is busy (${s}). You can upload without starting.`],
    [/^el puente «(.+)» no da señales \(último contacto: (.+)\)$/, (_, b, w) => `bridge “${b}” is silent (last seen: ${w === 'nunca' ? 'never' : w})`],
    [/^no responde \((.+)\)$/, (_, e) => `not responding (${e})`], [/^error HTTP (\d+)$/, (_, c) => `HTTP error ${c}`],
    [/^Enviado al puente: (.+) lo recibirá en unos segundos$/, (_, p) => `Sent to the bridge: ${p} will get it in a few seconds`],
    [/^(.+) imprimiendo (.+)$/, (_, p, f) => `${p} printing ${f}`], [/^Subido a (.+): (.+)$/, (_, p, f) => `Uploaded to ${p}: ${f}`],
    [/^Estás en la última versión \((.+)\)\.$/, (_, v) => `You are on the latest version (${v}).`], [/^Estás al día con main \((.+)\)\.$/, (_, v) => `Up to date with main (${v}).`],
    [/^Hay una versión nueva: (.+)$/, (_, v) => `New version available: ${v}`], [/^\(tienes (.+)\)$/, (_, v) => `(you have ${v})`],
    [/^Instalar (.+)$/, (_, v) => `Install ${v}`], [/^\(anterior guardada: (.+)\)$/, (_, v) => `(previous kept: ${v})`],
    [/^Datos importados(.*)$/, () => tr('Datos importados: revisa los materiales y pulsa Calcular')],
    [/^(.+): ¿cuántos envases de (.+) han entrado\?$/, (_, m, q) => `${m}: how many spools of ${q} came in?`],
    [/^(.+): ¿cuánto queda de verdad \((.+)\)\? Pesa las bobinas sin el carrete\.$/, (_, m, u) => `${m}: how much is really left (${u})? Weigh the filament without the spool.`],
    [/^¿Quién lo pagó\? \((.+)\)$/, (_, p) => `Who paid? (${p})`], [/^¿Borrar el usuario (.+)\?$/, (_, u) => `Delete user ${u}?`],
    [/^Nueva contraseña para (.+) \(mín\. 8\):$/, (_, u) => `New password for ${u} (min. 8):`], [/^¿A qué impresora\?$/, () => 'Which printer?'],
    [/^Subir a (.+)\.$/, (_, p) => `Upload to ${p}.`], [/^Aceptar = subir y EMPEZAR a imprimir ya$/, () => 'OK = upload and START printing now'],
    [/^Cancelar = solo subir \(lo arrancas tú desde la impresora\)$/, () => 'Cancel = upload only (start it yourself on the printer)'],
    [/^¿Seguro\? (.+) empezará a imprimir ahora\. Comprueba que la cama está libre y el filamento cargado\.$/, (_, p) => `Sure? ${p} will start printing now. Check the bed is clear and filament is loaded.`],
    [/^Ficha: (.+)$/, (_, k) => `Print sheet: ${tr(k)}`], [/^· (.+)$/, (_, k) => `· ${tr(k)}`],
    [/^GitHub respondió (\d+)$/, (_, c) => `GitHub answered ${c}`], [/^no se pudo consultar GitHub \((.+)\)$/, (_, e) => `could not reach GitHub (${e})`],
    [/^(.+) – últimos movimientos$/, (_, m) => `${m} – latest movements`], [/^Puente «(.+)» creado\.$/, (_, b) => `Bridge “${b}” created.`],
    [/^\((.+)\)$/, (_, a) => `(${t(a)})`],
  ];

  let LANG = 'es';
  function t(s) {
    if (LANG === 'es' || s == null) return s;
    const str = String(s);
    if (str.includes('\n')) return str.split('\n').map(t).join('\n');
    const m = str.match(/^(\s*)([\s\S]*?)(\s*)$/), core = m[2];
    if (!core) return str;
    if (core in EN) return m[1] + EN[core] + m[3];
    for (const [rx, fn] of RULES) { const r = core.match(rx); if (r) return m[1] + fn(...r) + m[3]; }
    if (core.includes(' · ')) { const parts = core.split(' · '), tp = parts.map(x => t(x)); if (tp.some((x, i) => x !== parts[i])) return m[1] + tp.join(' · ') + m[3]; }
    return str;
  }
  const ATTRS = ['placeholder', 'title', 'aria-label', 'alt', 'data-l'];
  // Se guarda el original (español) de cada texto traducido, para poder volver a español sin recargar.
  const ORIG = new WeakMap();
  function trText(n) {
    const cur = n.nodeValue, o = ORIG.get(n);
    const src = o && o.tr === cur ? o.orig : cur;
    const v = t(src);
    if (v !== src) { ORIG.set(n, {orig: src, tr: v}); if (v !== cur) n.nodeValue = v; }
  }
  function trAttr(el, a) {
    const cur = el.getAttribute(a), store = el.__trA || (el.__trA = {}), o = store[a];
    const src = o && o.tr === cur ? o.orig : cur;
    const v = t(src);
    if (v !== src) { store[a] = {orig: src, tr: v}; if (v !== cur) el.setAttribute(a, v); }
  }
  function translateNode(n) {
    if (LANG === 'es') return;
    if (n.nodeType === 3) {
      const p = n.parentElement;
      if (!p || /^(SCRIPT|STYLE|TEXTAREA|PRE|CODE)$/.test(p.tagName) || p.closest('[data-notr]')) return;
      trText(n);
      return;
    }
    if (n.nodeType !== 1 || n.hasAttribute('data-notr')) return;
    for (const a of ATTRS) if (n.hasAttribute(a)) trAttr(n, a);
    const tw = document.createTreeWalker(n, NodeFilter.SHOW_TEXT | NodeFilter.SHOW_ELEMENT);
    let c; while ((c = tw.nextNode())) {
      if (c.nodeType === 3) translateNode(c);
      else for (const a of ATTRS) if (c.hasAttribute(a)) trAttr(c, a);
    }
  }
  function restoreSpanish(root) {
    const tw = document.createTreeWalker(root, NodeFilter.SHOW_TEXT | NodeFilter.SHOW_ELEMENT);
    let c; while ((c = tw.nextNode())) {
      if (c.nodeType === 3) { const o = ORIG.get(c); if (o && c.nodeValue === o.tr) c.nodeValue = o.orig; ORIG.delete(c); }
      else if (c.__trA) { for (const [a, o] of Object.entries(c.__trA)) if (c.getAttribute(a) === o.tr) c.setAttribute(a, o.orig); delete c.__trA; }
    }
  }
  let obs = null;
  function setLang(l) {
    const prev = LANG;
    LANG = l === 'en' ? 'en' : 'es';
    document.documentElement.lang = LANG;
    if (obs) { obs.disconnect(); obs = null; }
    if (LANG === 'es') { if (prev === 'en') restoreSpanish(document.body); return; }
    translateNode(document.body);
    obs = new MutationObserver(ms => { for (const m of ms) {
      if (m.type === 'characterData') translateNode(m.target);
      else if (m.type === 'attributes') translateNode(m.target);
      else m.addedNodes.forEach(translateNode);
    } });
    obs.observe(document.body, {childList: true, subtree: true, characterData: true, attributes: true, attributeFilter: ATTRS});
  }
  for (const f of ['alert', 'confirm', 'prompt']) { const orig = window[f].bind(window); window[f] = (msg, ...r) => orig(t(msg), ...r); }
  window.I18N = {t, setLang, get lang() { return LANG; }, locale: () => (LANG === 'en' ? 'en-IE' : 'es-ES')};
  window.t = t;
})();
