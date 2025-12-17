-- ==========================================
-- SysStock - Database Multi-Tenant Único
-- ==========================================

CREATE DATABASE IF NOT EXISTS `sysstock` 
  DEFAULT CHARACTER SET utf8mb4 
  COLLATE utf8mb4_unicode_ci;

USE `sysstock`;

-- ==========================================
-- TABELA: empresas (Clientes/Tenants)
-- ==========================================
DROP TABLE IF EXISTS `empresas`;
CREATE TABLE `empresas` (
  `id` INT NOT NULL AUTO_INCREMENT,
  `tag` VARCHAR(50) NOT NULL COMMENT 'Identificador único usado no login (ex: zactiti)',
  `descricao` VARCHAR(100) NOT NULL COMMENT 'Nome da empresa',
  `ativo` CHAR(1) DEFAULT 'S',
  `data_cadastro` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_tag` (`tag`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ==========================================
-- TABELA: usuarios
-- ==========================================
DROP TABLE IF EXISTS `usuarios`;
CREATE TABLE `usuarios` (
  `id` INT NOT NULL AUTO_INCREMENT,
  `empresa_id` INT DEFAULT NULL COMMENT 'NULL = Master, INT = Empresa',
  `usuario` VARCHAR(50) NOT NULL,
  `senha` VARCHAR(255) NOT NULL COMMENT 'SHA256',
  `nome` VARCHAR(100) NOT NULL,
  `ativo` TINYINT(1) DEFAULT 1,
  `is_master` TINYINT(1) DEFAULT 0 COMMENT 'Acesso total ao sistema',
  `is_admin` TINYINT(1) DEFAULT 0 COMMENT 'Admin da empresa',
  `data_cadastro` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_usuario` (`usuario`),
  KEY `idx_empresa` (`empresa_id`),
  CONSTRAINT `fk_user_empresa` 
    FOREIGN KEY (`empresa_id`) 
    REFERENCES `empresas` (`id`) 
    ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ==========================================
-- TABELA: produtos
-- ==========================================
DROP TABLE IF EXISTS `produtos`;
CREATE TABLE `produtos` (
  `id` INT NOT NULL AUTO_INCREMENT,
  `empresa_id` INT NOT NULL,
  `codigo` VARCHAR(50) NOT NULL,
  `codigo_barras` VARCHAR(100) DEFAULT NULL,
  `descricao` VARCHAR(255) NOT NULL,
  `unidade` VARCHAR(10) DEFAULT 'UN',
  `quantidade` DECIMAL(10,3) DEFAULT 0.000,
  `preco_custo` DECIMAL(10,2) DEFAULT 0.00,
  `preco_venda` DECIMAL(10,2) DEFAULT 0.00,
  `ativo` TINYINT(1) DEFAULT 1,
  `data_cadastro` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_empresa_codigo` (`empresa_id`, `codigo`),
  KEY `idx_barras` (`codigo_barras`),
  KEY `idx_descricao` (`descricao`),
  CONSTRAINT `fk_prod_empresa` 
    FOREIGN KEY (`empresa_id`) 
    REFERENCES `empresas` (`id`) 
    ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ==========================================
-- TABELA: movimentacoes
-- ==========================================
DROP TABLE IF EXISTS `movimentacoes`;
CREATE TABLE `movimentacoes` (
  `id` INT NOT NULL AUTO_INCREMENT,
  `empresa_id` INT NOT NULL,
  `produto_id` INT NOT NULL,
  `tipo` ENUM('ENTRADA','SAIDA','AJUSTE','CONTAGEM') NOT NULL,
  `quantidade` DECIMAL(10,3) NOT NULL,
  `usuario_id` INT DEFAULT NULL,
  `data_hora` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_empresa` (`empresa_id`),
  KEY `idx_produto` (`produto_id`),
  KEY `idx_data` (`data_hora`),
  CONSTRAINT `fk_mov_empresa` 
    FOREIGN KEY (`empresa_id`) 
    REFERENCES `empresas` (`id`) 
    ON DELETE CASCADE,
  CONSTRAINT `fk_mov_prod` 
    FOREIGN KEY (`produto_id`) 
    REFERENCES `produtos` (`id`) 
    ON DELETE CASCADE,
  CONSTRAINT `fk_mov_user` 
    FOREIGN KEY (`usuario_id`) 
    REFERENCES `usuarios` (`id`) 
    ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ==========================================
-- TABELA: contagem_itens
-- ==========================================
DROP TABLE IF EXISTS `contagem_itens`;
CREATE TABLE `contagem_itens` (
  `id` INT NOT NULL AUTO_INCREMENT,
  `empresa_id` INT NOT NULL,
  `produto_id` INT NOT NULL,
  `quantidade` DECIMAL(10,3) NOT NULL,
  `data_registro` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_empresa` (`empresa_id`),
  KEY `idx_produto` (`produto_id`),
  CONSTRAINT `fk_cont_empresa` 
    FOREIGN KEY (`empresa_id`) 
    REFERENCES `empresas` (`id`) 
    ON DELETE CASCADE,
  CONSTRAINT `fk_cont_prod` 
    FOREIGN KEY (`produto_id`) 
    REFERENCES `produtos` (`id`) 
    ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ==========================================
-- VIEW: Estatísticas de Estoque por Empresa
-- ==========================================
DROP VIEW IF EXISTS `vw_valor_estoque`;
CREATE VIEW `vw_valor_estoque` AS
SELECT 
  p.empresa_id,
  COUNT(p.id) AS total_produtos,
  SUM(p.quantidade) AS quantidade_total,
  SUM(p.quantidade * p.preco_custo) AS valor_custo_total,
  SUM(p.quantidade * p.preco_venda) AS valor_venda_total,
  SUM(p.quantidade * (p.preco_venda - p.preco_custo)) AS lucro_potencial
FROM produtos p
WHERE p.ativo = 1
GROUP BY p.empresa_id;

-- ==========================================
-- DADOS INICIAIS
-- ==========================================

-- Usuário Master (acesso total ao sistema)
INSERT INTO `usuarios` (`empresa_id`, `usuario`, `senha`, `nome`, `ativo`, `is_master`, `is_admin`) 
VALUES (NULL, 'master', SHA2('master123', 256), 'Administrador MASTER', 1, 1, 1);

-- Empresa de Exemplo
INSERT INTO `empresas` (`tag`, `descricao`, `ativo`) 
VALUES ('zactiti', 'Zactiti Comércio e Serviços', 'S');

-- Admin da Empresa (vinculado à empresa id=1)
INSERT INTO `usuarios` (`empresa_id`, `usuario`, `senha`, `nome`, `ativo`, `is_master`, `is_admin`) 
VALUES (1, 'Carlos', SHA2('123', 256), 'Carlos Silva', 1, 0, 1);

-- Produtos de Exemplo
INSERT INTO `produtos` (`empresa_id`, `codigo`, `codigo_barras`, `descricao`, `unidade`, `quantidade`, `preco_custo`, `preco_venda`, `ativo`) 
VALUES 
  (1, '01', '7589764356821', 'Cabo SATA 50cm', 'UN', 15.000, 50.00, 150.00, 1),
  (1, '02', '7589764256821', 'SSD NVME 256GB Kingston', 'UN', 100.000, 200.00, 670.00, 1),
  (1, '03', '7891234567890', 'Memória RAM DDR4 8GB', 'UN', 50.000, 150.00, 350.00, 1);

-- ==========================================
-- VERIFICAÇÃO FINAL
-- ==========================================

-- Credenciais de Teste:
-- Master: empresa=MASTER, usuario=master, senha=master123
-- Empresa: empresa=zactiti, usuario=Carlos, senha=123