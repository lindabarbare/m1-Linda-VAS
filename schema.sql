-- Iesniegumi: datu modelis (minimums). Papildiniet, ja vajag.

CREATE TABLE temas (
    id        INTEGER PRIMARY KEY,
    nosaukums TEXT NOT NULL UNIQUE,
    apraksts  TEXT
);

CREATE TABLE iesniegumi (
    id            INTEGER PRIMARY KEY,
    numurs        TEXT NOT NULL UNIQUE,          -- piem., 2026-0001
    temas_id      INTEGER NOT NULL REFERENCES temas(id),
    vards         TEXT NOT NULL,
    epasts        TEXT NOT NULL,
    datu_apstrade_piekrita INTEGER NOT NULL CHECK (datu_apstrade_piekrita = 1),
    piekritis_laiks TEXT NOT NULL,
    adrese        TEXT,
    apraksts      TEXT NOT NULL,
    statuss       TEXT NOT NULL DEFAULT 'Jauns'  -- Jauns | Apstrādē | Atbildēts | Noraidīts
                  CHECK (statuss IN ('Jauns', 'Apstrādē', 'Atbildēts', 'Noraidīts')),
    atbilde       TEXT,
    izveidots     TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
    atjaunots     TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
);

CREATE TABLE notikumi (
    id            INTEGER PRIMARY KEY,
    iesnieguma_id INTEGER NOT NULL REFERENCES iesniegumi(id) ON DELETE CASCADE,
    laiks         TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
    veids         TEXT NOT NULL,                 -- statuss | komentars | atbilde | mi_ieteikums
    loma          TEXT,                          -- iedzivotajs | darbinieks | vaditajs | sistema
    teksts        TEXT NOT NULL
);

INSERT INTO temas (nosaukums, apraksts) VALUES
 ('Ielas un ceļi',        'Bedres, ceļa zīmes, ietves'),
 ('Apgaismojums',         'Nedeg vai bojāts ielu apgaismojums'),
 ('Atkritumi un vide',    'Nesavākti atkritumi, piesārņojums'),
 ('Bērnudārza rinda',     'Jautājumi par rindu un vietām'),
 ('Sociālā palīdzība',    'Pabalsti un sociālie pakalpojumi'),
 ('Cits',                 'Viss pārējais');

INSERT INTO iesniegumi (numurs, temas_id, vards, epasts, datu_apstrade_piekrita, piekritis_laiks, adrese, apraksts, statuss, atbilde, izveidots) VALUES
 ('2026-0001', 1, 'Anna Bērziņa',  'anna@example.lv', 1, '2026-10-06 09:10', 'Liepu iela 3',   'Liela bedre pretī mājai, bīstami velosipēdistiem.', 'Jauns', NULL, '2026-10-06 09:12'),
 ('2026-0002', 2, 'Jānis Ozols',   'janis@example.lv', 1, '2026-10-07 14:28', 'Skolas iela 12', 'Nedeg trīs laternas pēc kārtas.', 'Apstrādē', NULL, '2026-10-07 14:30'),
 ('2026-0003', 3, 'Līga Kalniņa',  'liga@example.lv',  1, '2026-10-01 08:03', 'Parka iela',     'Pārpildīts konteiners jau nedēļu.', 'Atbildēts', 'Konteiners iztukšots 03.10. Paldies par ziņojumu.', '2026-10-01 08:05'),
 ('2026-0004', 1, 'Ilze Liepiņa',  'ilze@example.lv',  1, '2026-10-08 11:40', 'Brīvības iela 8', 'Ietves posmā pie mājas ir pacēlušās bruģa plāksnes.', 'Jauns', NULL, '2026-10-08 11:42'),
 ('2026-0005', 2, 'Mārtiņš Zariņš','martins@example.lv',1, '2026-10-09 19:18', 'Dārza iela 5',   'Laterna pie gājēju pārejas iedegas ar pārtraukumiem.', 'Apstrādē', NULL, '2026-10-09 19:20'),
 ('2026-0006', 3, 'Elīna Kalēja',  'elina@example.lv', 1, '2026-10-10 10:05', 'Upes parks',     'Pie upes takas palikuši maisi ar atkritumiem.', 'Atbildēts', 'Teritorija sakopta 12.10.2026.', '2026-10-10 10:07'),
 ('2026-0007', 4, 'Rūta Eglīte',   'ruta@example.lv',  1, '2026-10-11 08:30', NULL,             'Kur var iepazīties ar informāciju par pašvaldības bērnudārzu rindām?', 'Jauns', NULL, '2026-10-11 08:32'),
 ('2026-0008', 4, 'Gatis Liepa',   'gatis@example.lv', 1, '2026-10-12 13:48', 'Skolas iela 4',  'Lūdzu precizēt, vai mans pieteikums bērnudārza rindai ir saņemts.', 'Apstrādē', NULL, '2026-10-12 13:50'),
 ('2026-0009', 5, 'Paula Kalniņa', 'paula@example.lv', 1, '2026-10-13 09:15', NULL,             'Kur var iepazīties ar pašvaldības sociālās palīdzības konsultāciju laikiem?', 'Atbildēts', 'Informācija par konsultāciju pieņemšanas laikiem sniegta iesnieguma atbildē.', '2026-10-13 09:17'),
 ('2026-0010', 5, 'Oskars Vītols', 'oskars@example.lv',1, '2026-10-14 07:55', 'Meža iela 12',  'Lūdzu norādīt, kādus dokumentus sagatavot konsultācijai par sociālajiem pakalpojumiem.', 'Jauns', NULL, '2026-10-14 07:57');

INSERT INTO notikumi (iesnieguma_id, veids, loma, teksts) VALUES
 (1, 'statuss', 'sistema',    'Iesniegums reģistrēts ar statusu «Jauns».'),
 (2, 'statuss', 'darbinieks', 'Statuss mainīts uz «Apstrādē».'),
 (3, 'atbilde', 'darbinieks', 'Konteiners iztukšots 03.10. Paldies par ziņojumu.');
