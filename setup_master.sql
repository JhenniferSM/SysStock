-- SCRIPT_MASTER.sql

-- 1. Cria ou seleciona o banco de dados central
CREATE DATABASE IF NOT EXISTS empresas CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci;
USE empresas;

DROP TABLE IF EXISTS `empresas`;
CREATE TABLE `empresas` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `tag` VARCHAR(50) NOT NULL UNIQUE COMMENT 'Tag usada no login (ex: zactiti)',
    `descricao` VARCHAR(100) NOT NULL,
    `host` VARCHAR(100) NOT NULL DEFAULT '127.0.0.1',
    `port` INT NOT NULL DEFAULT 3306,
    `user` VARCHAR(50) NOT NULL COMMENT 'Usuário do DB da empresa filha',
    `pass` VARCHAR(100) NOT NULL COMMENT 'Senha do DB da empresa filha',
    `base` VARCHAR(100) NOT NULL COMMENT 'Nome do DB da empresa filha',
    `ativo` CHAR(1) DEFAULT 'S' COMMENT 'S=Ativa, N=Inativa',
    `data_cadastro` TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- 3. Tabela de usuários para o ambiente MASTER (apenas para o login MASTER)
DROP TABLE IF EXISTS `usuarios`;
CREATE TABLE `usuarios` (
  `id` int NOT NULL AUTO_INCREMENT,
  `usuario` varchar(50) NOT NULL,
  `senha` varchar(255) NOT NULL,
  `nome` varchar(100) NOT NULL,
  `ativo` tinyint(1) DEFAULT '1',
  `is_master` tinyint(1) DEFAULT '0' COMMENT '1 se for o usuário master, 0 se for empresa filha.',
  PRIMARY KEY (`id`),
  UNIQUE KEY `usuario` (`usuario`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- 4. Insere o usuário MASTER (Empresa: MASTER, Usuário: master, Senha: master123)
-- SHA2(CONCAT('master123', 'chave_secreta_muito_forte_'), 224) 
-- Usando apenas o SHA2(senha, 224) para simplificar a demo (SHA224 é um alias)
INSERT INTO `usuarios` (`usuario`, `senha`, `nome`, `ativo`, `is_master`) 
VALUES ('master', SHA224('master123'), 'Administrador MASTER', 1, 1);

-- 5. Insere uma empresa de teste
INSERT INTO `empresas` (`tag`, `descricao`, `host`, `port`, `user`, `pass`, `base`, `ativo`) 
VALUES ('zactiti', 'ZacTiti Comércio e Serviços', '127.0.0.1', 3306, 'root', 'root', 'zactiti_estoque', 'S');

