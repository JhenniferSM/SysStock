-- SCRIPT_EMPRESA_ZACTITI.sql

-- 1. Cria ou seleciona o banco de dados da primeira empresa
CREATE DATABASE IF NOT EXISTS zactiti_estoque CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci;
USE zactiti_estoque;

-- 2. Tabela de Usuários (agora com is_admin)
DROP TABLE IF EXISTS `usuarios`;
CREATE TABLE `usuarios` (
  `id` int NOT NULL AUTO_INCREMENT,
  `usuario` varchar(50) NOT NULL,
  `senha_hash` varchar(255) NOT NULL,
  `nome` varchar(100) NOT NULL,
  `ativo` tinyint(1) DEFAULT '1',
  `is_admin` tinyint(1) DEFAULT '0' COMMENT '1 para administrador da empresa, 0 para usuário comum.',
  PRIMARY KEY (`id`),
  UNIQUE KEY `usuario` (`usuario`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- 3. Insere o usuário Administrador (Empresa: zactiti, Usuário: admin, Senha: 123456)
-- SHA2('123456', 256)
INSERT INTO `usuarios` (`usuario`, `senha_hash`, `nome`, `ativo`, `is_admin`) VALUES 
('admin', SHA2('123456', 256), 'Administrador Geral', 1, 1);


-- 4. Tabela de Produtos
DROP TABLE IF EXISTS `produtos`;
CREATE TABLE `produtos` (
  `id` int NOT NULL AUTO_INCREMENT,
  `codigo` varchar(50) NOT NULL COMMENT 'Código interno do produto',
  `codigo_barras` varchar(50) DEFAULT NULL COMMENT 'EAN/GTIN',
  `descricao` varchar(255) NOT NULL,
  `unidade` varchar(10) DEFAULT 'UN',
  `quantidade` decimal(10,3) NOT NULL DEFAULT '0.000',
  `estoque_minimo` decimal(10,3) DEFAULT '0.000',
  `preco_custo` decimal(10,2) NOT NULL DEFAULT '0.00',
  `preco_venda` decimal(10,2) NOT NULL DEFAULT '0.00',
  `ativo` tinyint(1) DEFAULT '1',
  `data_cadastro` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `codigo_UNIQUE` (`codigo`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- 5. Tabela de Movimentações (Histórico)
DROP TABLE IF EXISTS `movimentacoes`;
CREATE TABLE `movimentacoes` (
  `id` int NOT NULL AUTO_INCREMENT,
  `produto_id` int NOT NULL,
  `tipo` ENUM('ENTRADA', 'SAIDA', 'CONTAGEM', 'AJUSTE') NOT NULL,
  `quantidade` decimal(10,3) NOT NULL,
  `usuario_id` int DEFAULT NULL,
  `data_hora` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `fk_mov_prod_idx` (`produto_id`),
  KEY `fk_mov_user_idx` (`usuario_id`),
  CONSTRAINT `fk_mov_prod` FOREIGN KEY (`produto_id`) REFERENCES `produtos` (`id`),
  CONSTRAINT `fk_mov_user` FOREIGN KEY (`usuario_id`) REFERENCES `usuarios` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- 6. Tabela de Itens de Contagem (para o módulo de contagem/inventário)
DROP TABLE IF EXISTS `contagem_itens`;
CREATE TABLE `contagem_itens` (
  `id` int NOT NULL AUTO_INCREMENT,
  `produto_id` int NOT NULL,
  `quantidade` decimal(10,3) NOT NULL,
  `data_registro` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `fk_cont_prod_idx` (`produto_id`),
  CONSTRAINT `fk_cont_prod` FOREIGN KEY (`produto_id`) REFERENCES `produtos` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;


-- 7. View para facilitar o cálculo do valor total de estoque
DROP VIEW IF EXISTS `vw_valor_estoque`;
CREATE VIEW `vw_valor_estoque` AS
    SELECT 
        COUNT(p.id) AS total_produtos,
        SUM(p.quantidade) AS quantidade_total,
        SUM(p.quantidade * p.preco_custo) AS valor_custo_total,
        SUM(p.quantidade * p.preco_venda) AS valor_venda_total,
        SUM(p.quantidade * (p.preco_venda - p.preco_custo)) AS lucro_potencial
    FROM
        produtos p
    WHERE
        p.ativo = TRUE;