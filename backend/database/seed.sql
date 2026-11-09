BEGIN TRANSACTION;

-- =========================================================
-- 1) EQUIPOS: 48 equipo de ejemplo (ajustar IP reales luego)
-- =========================================================
INSERT INTO equipos (codigo, ip, nombre_host, tipo, ubicacion, estado, fecha_alta) VALUES
('PC-01', '192.168.1.10', 'AIP-PC-01', 'PC', 'Fila 1 - Puesto 1', 'activo', '2024-01-15 08:00:00'),
('PC-02', '192.168.1.11', 'AIP-PC-02', 'PC', 'Fila 1 - Puesto 2', 'activo', '2024-01-15 08:00:00'),
('PC-03', '192.168.1.12', 'AIP-PC-03', 'PC', 'Fila 1 - Puesto 3', 'activo', '2024-01-15 08:00:00'),
('PC-04', '192.168.1.13', 'AIP-PC-04', 'PC', 'Fila 1 - Puesto 4', 'activo', '2024-01-15 08:00:00'),
('PC-05', '192.168.1.14', 'AIP-PC-05', 'PC', 'Fila 1 - Puesto 5', 'activo', '2024-01-15 08:00:00'),
('PC-06', '192.168.1.15', 'AIP-PC-06', 'PC', 'Fila 1 - Puesto 6', 'activo', '2024-01-15 08:00:00'),
('PC-07', '192.168.1.16', 'AIP-PC-07', 'laptop', 'Fila 2 - Puesto 1', 'activo', '2024-01-15 08:00:00'),
('PC-08', '192.168.1.17', 'AIP-PC-08', 'laptop', 'Fila 2 - Puesto 2', 'activo', '2024-01-15 08:00:00'),
('PC-09', '192.168.1.18', 'AIP-PC-09', 'laptop', 'Fila 2 - Puesto 3', 'activo', '2024-01-15 08:00:00'),
('PC-10', '192.168.1.19', 'AIP-PC-10', 'laptop', 'Fila 2 - Puesto 4', 'activo', '2024-01-15 08:00:00'),
('PC-11', '192.168.1.20', 'AIP-PC-11', 'laptop', 'Fila 2 - Puesto 5', 'activo', '2024-01-15 08:00:00'),
('PC-12', '192.168.1.21', 'AIP-PC-12', 'laptop', 'Fila 2 - Puesto 6', 'activo', '2024-01-15 08:00:00'),
('PC-13', '192.168.1.22', 'AIP-PC-13', 'PC', 'Fila 3 - Puesto 1', 'activo', '2024-01-15 08:00:00'),
('PC-14', '192.168.1.23', 'AIP-PC-14', 'PC', 'Fila 3 - Puesto 2', 'activo', '2024-01-15 08:00:00'),
('PC-15', '192.168.1.24', 'AIP-PC-15', 'PC', 'Fila 3 - Puesto 3', 'activo', '2024-01-15 08:00:00'),
('PC-16', '192.168.1.25', 'AIP-PC-16', 'PC', 'Fila 3 - Puesto 4', 'activo', '2024-01-15 08:00:00'),
('PC-17', '192.168.1.26', 'AIP-PC-17', 'PC', 'Fila 3 - Puesto 5', 'activo', '2024-01-15 08:00:00'),
('PC-18', '192.168.1.27', 'AIP-PC-18', 'PC', 'Fila 3 - Puesto 6', 'activo', '2024-01-15 08:00:00'),
('PC-19', '192.168.1.28', 'AIP-PC-19', 'laptop', 'Fila 4 - Puesto 1', 'activo', '2024-01-15 08:00:00'),
('PC-20', '192.168.1.29', 'AIP-PC-20', 'laptop', 'Fila 4 - Puesto 2', 'activo', '2024-01-15 08:00:00'),
('PC-21', '192.168.1.30', 'AIP-PC-21', 'laptop', 'Fila 4 - Puesto 3', 'activo', '2024-01-15 08:00:00'),
('PC-22', '192.168.1.31', 'AIP-PC-22', 'laptop', 'Fila 4 - Puesto 4', 'activo', '2024-01-15 08:00:00'),
('PC-23', '192.168.1.32', 'AIP-PC-23', 'laptop', 'Fila 4 - Puesto 5', 'activo', '2024-01-15 08:00:00'),
('PC-24', '192.168.1.33', 'AIP-PC-24', 'laptop', 'Fila 4 - Puesto 6', 'activo', '2024-01-15 08:00:00'),
('PC-25', '192.168.1.34', 'AIP-PC-25', 'PC', 'Fila 5 - Puesto 1', 'activo', '2024-01-15 08:00:00'),
('PC-26', '192.168.1.35', 'AIP-PC-26', 'PC', 'Fila 5 - Puesto 2', 'activo', '2024-01-15 08:00:00'),
('PC-27', '192.168.1.36', 'AIP-PC-27', 'PC', 'Fila 5 - Puesto 3', 'activo', '2024-01-15 08:00:00'),
('PC-28', '192.168.1.37', 'AIP-PC-28', 'PC', 'Fila 5 - Puesto 4', 'activo', '2024-01-15 08:00:00'),
('PC-29', '192.168.1.38', 'AIP-PC-29', 'PC', 'Fila 5 - Puesto 5', 'activo', '2024-01-15 08:00:00'),
('PC-30', '192.168.1.39', 'AIP-PC-30', 'PC', 'Fila 5 - Puesto 6', 'activo', '2024-01-15 08:00:00'),
('PC-31', '192.168.1.40', 'AIP-PC-31', 'laptop', 'Fila 6 - Puesto 1', 'activo', '2024-01-15 08:00:00'),
('PC-32', '192.168.1.41', 'AIP-PC-32', 'laptop', 'Fila 6 - Puesto 2', 'activo', '2024-01-15 08:00:00'),
('PC-33', '192.168.1.42', 'AIP-PC-33', 'laptop', 'Fila 6 - Puesto 3', 'activo', '2024-01-15 08:00:00'),
('PC-34', '192.168.1.43', 'AIP-PC-34', 'laptop', 'Fila 6 - Puesto 4', 'activo', '2024-01-15 08:00:00'),
('PC-35', '192.168.1.44', 'AIP-PC-35', 'laptop', 'Fila 6 - Puesto 5', 'activo', '2024-01-15 08:00:00'),
('PC-36', '192.168.1.45', 'AIP-PC-36', 'laptop', 'Fila 6 - Puesto 6', 'activo', '2024-01-15 08:00:00'),
('PC-37', '192.168.1.46', 'AIP-PC-37', 'PC', 'Fila 7 - Puesto 1', 'activo', '2024-01-15 08:00:00'),
('PC-38', '192.168.1.47', 'AIP-PC-38', 'PC', 'Fila 7 - Puesto 2', 'activo', '2024-01-15 08:00:00'),
('PC-39', '192.168.1.48', 'AIP-PC-39', 'PC', 'Fila 7 - Puesto 3', 'activo', '2024-01-15 08:00:00'),
('PC-40', '192.168.1.49', 'AIP-PC-40', 'PC', 'Fila 7 - Puesto 4', 'activo', '2024-01-15 08:00:00'),
('PC-41', '192.168.1.50', 'AIP-PC-41', 'PC', 'Fila 7 - Puesto 5', 'activo', '2024-01-15 08:00:00'),
('PC-42', '192.168.1.51', 'AIP-PC-42', 'PC', 'Fila 7 - Puesto 6', 'activo', '2024-01-15 08:00:00'),
('PC-43', '192.168.1.52', 'AIP-PC-43', 'laptop', 'Fila 8 - Puesto 1', 'activo', '2024-01-15 08:00:00'),
('PC-44', '192.168.1.53', 'AIP-PC-44', 'laptop', 'Fila 8 - Puesto 2', 'activo', '2024-01-15 08:00:00'),
('PC-45', '192.168.1.54', 'AIP-PC-45', 'laptop', 'Fila 8 - Puesto 3', 'activo', '2024-01-15 08:00:00'),
('PC-46', '192.168.1.55', 'AIP-PC-46', 'laptop', 'Fila 8 - Puesto 4', 'activo', '2024-01-15 08:00:00'),
('PC-47', '192.168.1.56', 'AIP-PC-47', 'laptop', 'Fila 8 - Puesto 5', 'activo', '2024-01-15 08:00:00'),
('PC-48', '192.168.1.57', 'AIP-PC-48', 'laptop', 'Fila 8 - Puesto 6', 'activo', '2024-01-15 08:00:00');

-- =========================================================
-- 2) ALUMNOS: 25 registros ficticios
-- =========================================================
INSERT INTO alumnos (codigo_alumno, nombres, apellidos, grado, seccion, activo, pin_hash) VALUES
('ALU-001', 'Mateo', 'García', 1, 'A', 1, 'hash_demo_001'),
('ALU-002', 'Sofía', 'Rojas', 1, 'A', 1, 'hash_demo_002'),
('ALU-003', 'Nicolás', 'López', 1, 'B', 1, 'hash_demo_003'),
('ALU-004', 'Valentina', 'Pérez', 1, 'B', 1, 'hash_demo_004'),
('ALU-005', 'Tomás', 'Fernández', 1, 'C', 1, 'hash_demo_005'),
('ALU-006', 'Martina', 'Silva', 2, 'A', 1, 'hash_demo_006'),
('ALU-007', 'Lucas', 'Díaz', 2, 'A', 1, 'hash_demo_007'),
('ALU-008', 'Renata', 'Morales', 2, 'B', 1, 'hash_demo_008'),
('ALU-009', 'Damián', 'Vargas', 2, 'B', 1, 'hash_demo_009'),
('ALU-010', 'Agustina', 'Castro', 2, 'C', 1, 'hash_demo_010'),
('ALU-011', 'Facundo', 'Muñoz', 3, 'A', 1, 'hash_demo_011'),
('ALU-012', 'Camila', 'Reyes', 3, 'A', 1, 'hash_demo_012'),
('ALU-013', 'Bruno', 'Torres', 3, 'B', 1, 'hash_demo_013'),
('ALU-014', 'Luna', 'Méndez', 3, 'B', 1, 'hash_demo_014'),
('ALU-015', 'Emiliano', 'Cárdenas', 3, 'C', 1, 'hash_demo_015'),
('ALU-016', 'Julieta', 'Paredes', 4, 'A', 1, 'hash_demo_016'),
('ALU-017', 'Leandro', 'Molina', 4, 'A', 1, 'hash_demo_017'),
('ALU-018', 'Abril', 'Espinoza', 4, 'B', 1, 'hash_demo_018'),
('ALU-019', 'Matías', 'Romero', 4, 'B', 1, 'hash_demo_019'),
('ALU-020', 'Florencia', 'Nieto', 4, 'C', 1, 'hash_demo_020'),
('ALU-021', 'Benjamín', 'Ortega', 5, 'A', 1, 'hash_demo_021'),
('ALU-022', 'Catalina', 'Guzmán', 5, 'A', 1, 'hash_demo_022'),
('ALU-023', 'Joaquín', 'Sánchez', 5, 'B', 1, 'hash_demo_023'),
('ALU-024', 'Isidora', 'Bustos', 5, 'B', 1, 'hash_demo_024'),
('ALU-025', 'Thiago', 'Navarro', 5, 'C', 1, 'hash_demo_025');

-- =========================================================
-- 3) USUARIO ADMIN DE EJEMPLO
-- =========================================================
INSERT INTO usuarios_admin (usuario, password_hash, nombre_completo, rol, activo, fecha_creacion) VALUES
('admin', 'HASH_PENDIENTE_REEMPLAZAR_CON_INIT_DB', 'Administrador de ejemplo', 'admin', 1, '2024-01-01 08:00:00');

-- =========================================================
-- 4) SESIONES DE EJEMPLO
-- =========================================================
INSERT INTO sesiones (alumno_id, equipo_id, fecha_hora_inicio, fecha_hora_fin, ultimo_latido, tipo_cierre, cerrado_por, observacion) VALUES
(1, 1, '2025-10-01 08:05:00', '2025-10-01 09:40:00', '2025-10-01 09:39:00', 'alumno', 1, 'Trabajo en Word y navegador.'),
(2, 2, '2025-10-01 10:00:00', '2025-10-01 11:20:00', '2025-10-01 11:19:00', 'automatico', 1, 'Cierre por inactividad del equipo.'),
(3, 3, '2025-10-02 08:15:00', '2025-10-02 10:00:00', '2025-10-02 09:59:00', 'admin', 1, 'Uso normal durante clase.'),
(4, 4, '2025-10-02 11:00:00', '2025-10-02 12:30:00', '2025-10-02 12:29:00', 'alumno', 1, 'Entrega de tarea.'),
(15, 12, '2025-11-01 08:30:00', NULL, '2025-11-01 08:35:00', NULL, NULL, 'Sesión activa actualmente.'),
(6, 20, '2025-11-01 08:40:00', NULL, '2025-11-01 08:42:00', NULL, NULL, 'Alumno en línea en esta sesión.'),
(21, 41, '2025-11-01 09:00:00', '2025-11-01 09:45:00', '2025-11-01 09:44:00', 'reemplazo', 1, 'Reemplazo por cambio de alumno.');

-- =========================================================
-- 5) INCIDENCIAS DE EJEMPLO
-- =========================================================
INSERT INTO incidencias (equipo_id, descripcion, severidad, estado, fecha_hora_reporte, reportado_por, sesion_probable_id, fecha_resolucion, solucion) VALUES
(12, 'Pantalla con líneas verticales y brillo irregular.', 'grave', 'resuelta', '2025-11-01 10:15:00', 1, 5, '2025-11-01 10:40:00', 'Se reemplazó la pantalla y se revisó el cable de video.'),
(20, 'Equipo muy lento y se apaga solo al abrir varios programas.', 'moderada', 'en_revision', '2025-11-01 09:55:00', 1, 6, NULL, NULL),
(41, 'Mouse sin respuesta y teclado desconectado.', 'leve', 'abierta', '2025-11-01 11:10:00', 1, 7, NULL, NULL);

COMMIT;
