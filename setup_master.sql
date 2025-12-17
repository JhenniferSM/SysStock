CREATE DATABASE  IF NOT EXISTS `sysstock` /*!40100 DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci */ /*!80016 DEFAULT ENCRYPTION='N' */;
USE `sysstock`;
-- MySQL dump 10.13  Distrib 8.0.43, for Win64 (x86_64)
--
-- Host: 127.0.0.1    Database: sysstock
-- ------------------------------------------------------
-- Server version	8.0.43

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!50503 SET NAMES utf8 */;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0 */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;

--
-- Table structure for table `contagem_itens`
--

DROP TABLE IF EXISTS `contagem_itens`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `contagem_itens` (
  `id` int NOT NULL AUTO_INCREMENT,
  `empresa_id` int NOT NULL,
  `produto_id` int NOT NULL,
  `quantidade` decimal(10,3) NOT NULL,
  `data_registro` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `fk_cont_empresa` (`empresa_id`),
  KEY `fk_cont_prod` (`produto_id`),
  CONSTRAINT `fk_cont_empresa` FOREIGN KEY (`empresa_id`) REFERENCES `empresas` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_cont_prod` FOREIGN KEY (`produto_id`) REFERENCES `produtos` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `contagem_itens`
--

LOCK TABLES `contagem_itens` WRITE;
/*!40000 ALTER TABLE `contagem_itens` DISABLE KEYS */;
/*!40000 ALTER TABLE `contagem_itens` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `empresas`
--

DROP TABLE IF EXISTS `empresas`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `empresas` (
  `id` int NOT NULL AUTO_INCREMENT,
  `tag` varchar(50) NOT NULL COMMENT 'Usada no login (ex: zactiti)',
  `descricao` varchar(100) NOT NULL,
  `ativo` char(1) DEFAULT 'S',
  `data_cadastro` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `tag` (`tag`)
) ENGINE=InnoDB AUTO_INCREMENT=2 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `empresas`
--

LOCK TABLES `empresas` WRITE;
/*!40000 ALTER TABLE `empresas` DISABLE KEYS */;
INSERT INTO `empresas` VALUES (1,'zactiti','Zactiti Comércio e Serviços','S','2025-12-17 00:46:35');
/*!40000 ALTER TABLE `empresas` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `movimentacoes`
--

DROP TABLE IF EXISTS `movimentacoes`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `movimentacoes` (
  `id` int NOT NULL AUTO_INCREMENT,
  `empresa_id` int NOT NULL,
  `produto_id` int NOT NULL,
  `tipo` enum('ENTRADA','SAIDA','AJUSTE','CONTAGEM') NOT NULL,
  `quantidade` decimal(10,3) NOT NULL,
  `usuario_id` int DEFAULT NULL,
  `data_hora` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `fk_mov_empresa` (`empresa_id`),
  KEY `fk_mov_prod` (`produto_id`),
  KEY `fk_mov_user` (`usuario_id`),
  CONSTRAINT `fk_mov_empresa` FOREIGN KEY (`empresa_id`) REFERENCES `empresas` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_mov_prod` FOREIGN KEY (`produto_id`) REFERENCES `produtos` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_mov_user` FOREIGN KEY (`usuario_id`) REFERENCES `usuarios` (`id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `movimentacoes`
--

LOCK TABLES `movimentacoes` WRITE;
/*!40000 ALTER TABLE `movimentacoes` DISABLE KEYS */;
/*!40000 ALTER TABLE `movimentacoes` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `produtos`
--

DROP TABLE IF EXISTS `produtos`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `produtos` (
  `id` int NOT NULL AUTO_INCREMENT,
  `empresa_id` int NOT NULL,
  `codigo` varchar(50) NOT NULL,
  `codigo_barras` varchar(100) DEFAULT NULL,
  `descricao` varchar(255) NOT NULL,
  `unidade` varchar(10) DEFAULT 'UN',
  `quantidade` decimal(10,3) DEFAULT '0.000',
  `preco_custo` decimal(10,2) DEFAULT '0.00',
  `preco_venda` decimal(10,2) DEFAULT '0.00',
  `ativo` tinyint(1) DEFAULT '1',
  `data_cadastro` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_empresa_codigo` (`empresa_id`,`codigo`),
  CONSTRAINT `fk_prod_empresa` FOREIGN KEY (`empresa_id`) REFERENCES `empresas` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=3 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `produtos`
--

LOCK TABLES `produtos` WRITE;
/*!40000 ALTER TABLE `produtos` DISABLE KEYS */;
INSERT INTO `produtos` VALUES (1,1,'01','758976435682','Cabo SATA','UN',1.000,50.00,150.00,1,'2025-12-17 00:46:35'),(2,1,'02','7589764256821','SSD NVME 256GB','UN',100.000,200.00,670.00,1,'2025-12-17 00:46:35');
/*!40000 ALTER TABLE `produtos` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `usuarios`
--

DROP TABLE IF EXISTS `usuarios`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `usuarios` (
  `id` int NOT NULL AUTO_INCREMENT,
  `empresa_id` int DEFAULT NULL,
  `usuario` varchar(50) NOT NULL,
  `senha` varchar(255) NOT NULL,
  `nome` varchar(100) NOT NULL,
  `ativo` tinyint(1) DEFAULT '1',
  `is_master` tinyint(1) DEFAULT '0',
  `is_admin` tinyint(1) DEFAULT '0',
  `data_cadastro` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `usuario` (`usuario`),
  KEY `fk_user_empresa` (`empresa_id`),
  CONSTRAINT `fk_user_empresa` FOREIGN KEY (`empresa_id`) REFERENCES `empresas` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=3 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `usuarios`
--

LOCK TABLES `usuarios` WRITE;
/*!40000 ALTER TABLE `usuarios` DISABLE KEYS */;
INSERT INTO `usuarios` VALUES (1,NULL,'master','e7bc2f973afb8dfaf00fadfb19596741108be08ab4a107c6a799c429b684c64a','Administrador MASTER',1,1,1,'2025-12-17 00:46:35'),(2,1,'Carlos','8d969eef6ecad3c29a3a629280e686cf0c3f5d5a86aff3ca12020c923adc6c92','Carlos',1,0,1,'2025-12-17 00:46:35');
/*!40000 ALTER TABLE `usuarios` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Temporary view structure for view `vw_valor_estoque`
--

DROP TABLE IF EXISTS `vw_valor_estoque`;
/*!50001 DROP VIEW IF EXISTS `vw_valor_estoque`*/;
SET @saved_cs_client     = @@character_set_client;
/*!50503 SET character_set_client = utf8mb4 */;
/*!50001 CREATE VIEW `vw_valor_estoque` AS SELECT 
 1 AS `empresa_id`,
 1 AS `total_produtos`,
 1 AS `quantidade_total`,
 1 AS `valor_custo_total`,
 1 AS `valor_venda_total`,
 1 AS `lucro_potencial`*/;
SET character_set_client = @saved_cs_client;

--
-- Dumping events for database 'sysstock'
--

--
-- Dumping routines for database 'sysstock'
--

--
-- Final view structure for view `vw_valor_estoque`
--

/*!50001 DROP VIEW IF EXISTS `vw_valor_estoque`*/;
/*!50001 SET @saved_cs_client          = @@character_set_client */;
/*!50001 SET @saved_cs_results         = @@character_set_results */;
/*!50001 SET @saved_col_connection     = @@collation_connection */;
/*!50001 SET character_set_client      = utf8mb4 */;
/*!50001 SET character_set_results     = utf8mb4 */;
/*!50001 SET collation_connection      = utf8mb4_0900_ai_ci */;
/*!50001 CREATE ALGORITHM=UNDEFINED */
/*!50013 DEFINER=`root`@`localhost` SQL SECURITY DEFINER */
/*!50001 VIEW `vw_valor_estoque` AS select `produtos`.`empresa_id` AS `empresa_id`,count(`produtos`.`id`) AS `total_produtos`,sum(`produtos`.`quantidade`) AS `quantidade_total`,sum((`produtos`.`quantidade` * `produtos`.`preco_custo`)) AS `valor_custo_total`,sum((`produtos`.`quantidade` * `produtos`.`preco_venda`)) AS `valor_venda_total`,sum((`produtos`.`quantidade` * (`produtos`.`preco_venda` - `produtos`.`preco_custo`))) AS `lucro_potencial` from `produtos` where (`produtos`.`ativo` = 1) group by `produtos`.`empresa_id` */;
/*!50001 SET character_set_client      = @saved_cs_client */;
/*!50001 SET character_set_results     = @saved_cs_results */;
/*!50001 SET collation_connection      = @saved_col_connection */;
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2025-12-16 21:52:28
