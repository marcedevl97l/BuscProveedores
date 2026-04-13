// Detectar cuando se cierra la pestaña
window.addEventListener('beforeunload', function () {
    navigator.sendBeacon('/ping');
});

// Mantener viva la conexión cada 20 segundos
setInterval(function () {
    fetch('/ping').catch(err => console.log('Servidor cerrado'));
}, 20000);

// Toggle entre vistas
function toggleView(view) {
    const comparisonView = document.getElementById('comparison-view');
    const listView = document.getElementById('list-view');
    const comparisonBtn = document.getElementById('comparison-btn');
    const listBtn = document.getElementById('list-btn');

    if (view === 'comparison') {
        comparisonView.classList.add('active');
        listView.classList.remove('active');
        comparisonBtn.classList.add('active');
        listBtn.classList.remove('active');
    } else {
        comparisonView.classList.remove('active');
        listView.classList.add('active');
        comparisonBtn.classList.remove('active');
        listBtn.classList.add('active');
    }
}

// Carrito de compras
let cart = JSON.parse(sessionStorage.getItem('cart')) || [];

function updateCartDisplay() {
    const cartItems = document.getElementById('cart-items');
    const cartTotal = document.getElementById('cart-total');
    const cartCount = document.getElementById('cart-count');

    cartItems.innerHTML = '';
    let total = 0;
    let count = 0;

    // Agrupar por fuente
    const groupedCart = {};
    cart.forEach(item => {
        if (!groupedCart[item.fuente]) {
            groupedCart[item.fuente] = [];
        }
        const base = item.precioBase !== undefined && item.precioBase !== null ? item.precioBase : item.precio;
        const precioItem = getEffectivePrice(base, item.escala, item.precioEscala, item.cantidad);
        item.precioBase = base;
        item.precio = precioItem;
        item.subtotal = precioItem * item.cantidad;
        groupedCart[item.fuente].push(item);
        total += item.subtotal;
        count += item.cantidad;
    });

    for (const [fuente, items] of Object.entries(groupedCart)) {
        const fuenteHeader = document.createElement('div');
        fuenteHeader.style.cssText = 'font-size: 11px; font-weight: 800; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.5px; margin: 15px 0 10px 5px;';
        fuenteHeader.innerHTML = fuente;
        cartItems.appendChild(fuenteHeader);

        items.forEach((item, index) => {
            const itemDiv = document.createElement('div');
            itemDiv.className = 'cart-item';
            itemDiv.innerHTML = `
                <span class="cart-item-name">${item.nombre}</span>
                <div class="cart-item-details">
                    <span style="font-weight: 500; font-size: 11px; margin-bottom: 8px; display: block;">${item.proveedor}</span>
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <div class="quantity-controls" style="padding: 2px;">
                            <button class="qty-btn" style="width: 24px; height: 24px; font-size: 12px; border-radius: 6px;" onclick="changeCartQuantity('${fuente}', ${index}, -1)">-</button>
                            <span class="qty-input" style="width: 30px; line-height: 24px;">${item.cantidad}</span>
                            <button class="qty-btn" style="width: 24px; height: 24px; font-size: 12px; border-radius: 6px;" onclick="changeCartQuantity('${fuente}', ${index}, 1)">+</button>
                        </div>
                        <span class="cart-item-price" style="font-family: 'JetBrains Mono', monospace; font-weight: 800; font-size: 14px;">S/ ${item.subtotal.toFixed(2)}</span>
                    </div>
                </div>
                <button class="remove-btn" onclick="removeFromCart('${fuente}', ${index})" style="position: absolute; top: 12px; right: 12px; background: none; border: none; cursor: pointer; font-size: 14px;">🗑️</button>
            `;
            cartItems.appendChild(itemDiv);
        });
    }

    cartTotal.textContent = total.toFixed(2);
    cartCount.textContent = count;
    sessionStorage.setItem('cart', JSON.stringify(cart));
}

function addToCartFromButton(button) {
    const nombre = button.dataset.nombre;
    const proveedor = button.dataset.proveedor;
    const fuente = button.dataset.fuente;
    const container = button.closest('.product-card') || button.closest('tr');
    const qtyInput = container ? container.querySelector('.qty-input') : null;
    const cantidad = qtyInput ? parseInt(qtyInput.value, 10) || 1 : 1;

    const base = parseNumber(button.dataset.precioBase);
    const escala = parseNumber(button.dataset.escala);
    const precioEscala = parseNumber(button.dataset.precioEscala);
    const precio = getEffectivePrice(base, escala, precioEscala, cantidad);

    addToCart(nombre, proveedor, precio, fuente, button, cantidad, base, escala, precioEscala);
}

function addToCart(nombre, proveedor, precio, fuente, button, cantidad, base, escala, precioEscala) {
    const subtotal = precio * cantidad;

    // Verificar si ya existe el producto
    const existingIndex = cart.findIndex(item => item.nombre === nombre && item.proveedor === proveedor && item.fuente === fuente);

    if (existingIndex >= 0) {
        cart[existingIndex].cantidad += cantidad;
        cart[existingIndex].precio = getEffectivePrice(
            cart[existingIndex].precioBase,
            cart[existingIndex].escala,
            cart[existingIndex].precioEscala,
            cart[existingIndex].cantidad
        );
        cart[existingIndex].subtotal = cart[existingIndex].precio * cart[existingIndex].cantidad;
    } else {
        cart.push({
            nombre: nombre,
            proveedor: proveedor,
            precio: precio,
            precioBase: base,
            escala: escala,
            precioEscala: precioEscala,
            fuente: fuente,
            cantidad: cantidad,
            subtotal: subtotal
        });
    }

    updateCartDisplay();
    // Animación de feedback
    button.textContent = '✅ Agregado';
    setTimeout(() => {
        button.innerHTML = '🛒 Agregar al Carrito';
    }, 1000);
}

function removeFromCart(fuente, index) {
    const fuenteItems = cart.filter(item => item.fuente === fuente);
    cart.splice(cart.indexOf(fuenteItems[index]), 1);
    updateCartDisplay();
}

function changeCartQuantity(fuente, index, delta) {
    const fuenteItems = cart.filter(item => item.fuente === fuente);
    const item = fuenteItems[index];
    item.cantidad = Math.max(1, item.cantidad + delta);
    item.precio = getEffectivePrice(item.precioBase, item.escala, item.precioEscala, item.cantidad);
    item.subtotal = item.precio * item.cantidad;
    updateCartDisplay();
}

function updateCartSubtotal(fuente, index, newQty) {
    const fuenteItems = cart.filter(item => item.fuente === fuente);
    const item = fuenteItems[index];
    item.cantidad = Math.max(1, parseInt(newQty) || 1);
    item.precio = getEffectivePrice(item.precioBase, item.escala, item.precioEscala, item.cantidad);
    item.subtotal = item.precio * item.cantidad;
    updateCartDisplay();
}

function changeQuantity(button, delta) {
    const input = button.parentElement.querySelector('.qty-input');
    const newValue = Math.max(1, parseInt(input.value) + delta);
    input.value = newValue;
    updateSubtotal(input);
}

function updateSubtotal(input) {
    const container = input.closest('.product-card') || input.closest('tr');
    if (!container) return;

    const base = parseNumber(container.dataset.precioBase);
    const escala = parseNumber(container.dataset.escala);
    const precioEscala = parseNumber(container.dataset.precioEscala);
    if (base === null) return;

    const cantidad = Math.max(1, parseInt(input.value, 10) || 1);
    const usingScale = escala !== null && precioEscala !== null && cantidad >= escala;
    const precio = usingScale ? precioEscala : base;

    const priceValue = container.querySelector('.price-value');
    if (priceValue) {
        priceValue.textContent = precio.toFixed(2);
    }

    const scaleBadge = container.querySelector('.scale-badge');
    if (scaleBadge) {
        scaleBadge.style.display = usingScale ? 'inline' : 'none';
    }
}

function toggleCart() {
    const panel = document.getElementById('cart-panel');
    panel.classList.toggle('active');
}

function exportToExcel() {
    if (cart.length === 0) {
        alert('El carrito está vacío');
        return;
    }

    fetch('/export_cart', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(cart)
    })
        .then(response => {
            if (response.ok) {
                return response.blob();
            } else {
                throw new Error('Error al exportar');
            }
        })
        .then(blob => {
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = 'lista_compras.xlsx';
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
            document.body.removeChild(a);
        })
        .catch(error => {
            console.error('Error:', error);
            alert('Error al exportar el documento');
        });
}

// Inicializar carrito al cargar la página
document.addEventListener('DOMContentLoaded', function () {
    updateCartDisplay();
});

function parseNumber(value) {
    const num = parseFloat(value);
    return Number.isFinite(num) ? num : null;
}

function getEffectivePrice(base, escala, precioEscala, cantidad) {
    if (escala !== null && precioEscala !== null && cantidad >= escala) {
        return precioEscala;
    }
    return base;
}