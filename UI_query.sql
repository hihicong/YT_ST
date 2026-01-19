
CREATE TABLE `yt_channel_statistics`.`UI_query`  (
    `iD` bigint unsigned NOT NULL AUTO_INCREMENT,
    `DateTime` DATETIME NOT NULL,
    `QuerySec` int(255) NOT NULL,
	`Message` TEXT NOT NULL,
	`DataSize` int(255) NOT NULL,
    `AppVer` VARCHAR(255) NOT NULL,
    PRIMARY KEY (`id`)
) 
ENGINE = InnoDB 
DEFAULT 
CHARSET = utf8mb4;
;
;
ALTER TABLE `yt_channel_statistics`.`UI_query`
CONVERT TO CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
;
;
;
;
CREATE INDEX `IDX_DateTime` ON `yt_channel_statistics`.`UI_query` (`DateTime` DESC);
CREATE INDEX `IDX_QuerySec` ON `yt_channel_statistics`.`UI_query` (`QuerySec` DESC);
CREATE INDEX `IDX_Message` ON `yt_channel_statistics`.`UI_query` (`Message`(191) DESC);
CREATE INDEX `IDX_AppVer` ON `yt_channel_statistics`.`UI_query` (`AppVer`(191) DESC);
CREATE INDEX `IDX_DataSize` ON `yt_channel_statistics`.`UI_query` (`DataSize`(191) DESC);

;
;
;
Truncate table `yt_channel_statistics`.`UI_query` ;
ALTER TABLE `yt_channel_statistics`.`UI_query`  AUTO_INCREMENT = 1;
;
;
;--
;#
;
;
SHOW INDEXES FROM `yt_channel_statistics`.`UI_query`;
;
-- 
;
DELIMITER $$

CREATE PROCEDURE `yt_channel_statistics`.`sp_UI_query`(
    `@DateTime` DATETIME,
    `@QuerySec` int(255),
    `@Message` TEXT CHARACTER SET 'utf8' COLLATE 'utf8_general_ci',
	`@DataSize` int(255),
    `@AppVer`  VARCHAR(255) CHARACTER SET 'utf8' COLLATE 'utf8_general_ci'
)
BEGIN
	INSERT INTO `yt_channel_statistics`.`UI_query` (
		`DateTime`, 
		`QuerySec`, 
		`Message`,
		`DataSize`,
		`AppVer`

	) 
	VALUES (
		`@DateTime`, 
		`@QuerySec`, 
		`@Message`, 
        `@DataSize`,
		`@AppVer`
	);
END
$$

DELIMITER ;

;

#################################################
-- 不要亂動
CALL yt_channel_statistics.sp_UI_query(
  '2025-10-03 10:34:02',
  '123',
  '測試頻道',
  '456',
  'category_test'
);
SELECT * FROM  `yt_channel_statistics`.`UI_query`;
SHOW FULL COLUMNS FROM `yt_channel_statistics`.`UI_query`;
########################################################


