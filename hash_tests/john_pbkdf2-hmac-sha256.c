/* Low iteration test vectors for comparison */
{"$pbkdf2-sha256$1000$b1dWS2dab3dKQWhPSUg3cg$UY9j5wlyxtsJqhDKTqua8Q3fMp0ojc2pOnErzr8ntLE", "magnum"},
{"$pbkdf2-sha256$1000$amkzNk9tOXJVZ043QTZ1dA$YIpbl0hjiV9UFMszHNDlJIa0bcObTIkPzT6XvhJPcMM", "bonum"},
{"$pbkdf2-sha256$1000$WEI2ZTVJcWdTZ3JQQjVnMA$6n1V7Ffm1tsB4q7uk4mi8z5Sco.fL28pScSSc5Qr27Y", "Ripper"},
{"$pbkdf2-sha256$10000$UWthWUhuRXdPZkZPMnF0Ug$l/T9Bmy7qtaPEvbPC2qAfYuj5RAxTbv8I.hSTfyIwYg", "10K worth of looping"},
{"$pbkdf2-sha256$10000$Sm1hNlBZWDVYd1FWT3FUUQ$foweCatpTeXpaba1tS7fJTPUquByBb5oI8vilOSspaI", "moebusring"},
{"$pbkdf2-sha256$12000$2NtbSwkhRChF6D3nvJfSGg$OEWLc4keep8Vx3S/WnXgsfalb9q0RQdS1s05LfalSG4", ""},
{"$pbkdf2-sha256$12000$fK8VAoDQuvees5ayVkpp7Q$xfzKAoBR/Iaa68tjn.O8KfGxV.zdidcqEeDoTFvDz2A", "1"},
{"$pbkdf2-sha256$12000$GoMQYsxZ6/0fo5QyhtAaAw$xQ9L6toKn0q245SIZKoYjCu/Fy15hwGme9.08hBde1w", "12"},
{"$pbkdf2-sha256$12000$6r3XWgvh/D/HeA/hXAshJA$11YY39OaSkJuwb.ONKVy5ebCZ00i5f8Qpcgwfe3d5kY", "123"},
{"$pbkdf2-sha256$12000$09q711rLmbMWYgwBIGRMqQ$kHdAHlnQ1i1FHKBCPLV0sA20ai2xtYA1Ev8ODfIkiQg", "1234"},
{"$pbkdf2-sha256$12000$Nebce08pJcT43zuHUMo5Rw$bMW/EsVqy8tMaDecFwuZNEPVfQbXBclwN78okLrxJoA", "openwall"},
{"$pbkdf2-sha256$12000$mtP6/39PSQlhzBmDsJZS6g$zUXxf/9XBGrkedXVwhpC9wLLwwKSvHX39QRz7MeojYE", "password"},
{"$pbkdf2-sha256$12000$35tzjhGi9J5TSilF6L0XAg$MiJA1gPN1nkuaKPVzSJMUL7ucH4bWIQetzX/JrXRYpw", "pbkdf2-sha256"},
{"$pbkdf2-sha256$12000$sxbCeE8pxVjL2ds7hxBizA$uIiwKdo9DbPiiaLi1y3Ljv.r9G1tzxLRdlkD1uIOwKM", " 15 characters "},
{"$pbkdf2-sha256$12000$CUGI8V7rHeP8nzMmhJDyXg$qjq3rBcsUgahqSO/W4B1bvsuWnrmmC4IW8WKMc5bKYE", " 16 characters__"},
{"$pbkdf2-sha256$12000$FmIM4VxLaY1xLuWc8z6n1A$OVe6U1d5dJzYFKlJsZrW1NzUrfgiTpb9R5cAfn96WCk", " 20 characters______"},
{"$pbkdf2-sha256$12000$fA8BAMAY41wrRQihdO4dow$I9BSCuV6UjG55LktTKbV.bIXtyqKKNvT3uL7JQwMLp8", " 24 characters______1234"},
{"$pbkdf2-sha256$12000$/j8npJTSOmdMKcWYszYGgA$PbhiSNRzrELfAavXEsLI1FfitlVjv9NIB.jU1HHRdC8", " 28 characters______12345678"},
{"$pbkdf2-sha256$12000$xfj/f6/1PkcIoXROCeE8Bw$ci.FEcPOKKKhX5b3JwzSDo6TGuYjgj1jKfCTZ9UpDM0", " 32 characters______123456789012"},
{"$pbkdf2-sha256$12000$6f3fW8tZq7WWUmptzfmfEw$GDm/yhq1TnNR1MVGy73UngeOg9QJ7DtW4BnmV2F065s", " 40 characters______12345678901234567890"},
{"$pbkdf2-sha256$12000$dU5p7T2ndM7535tzjpGyVg$ILbppLkipmonlfH1I2W3/vFMyr2xvCI8QhksH8DWn/M", " 55 characters______________________________________end"},
{"$pbkdf2-sha256$12000$iDFmDCHE2FtrDaGUEmKMEaL0Xqv1/t/b.x.DcC6lFEI$tUdEcw3csCnsfiYbFdXH6nvbftH8rzvBDl1nABeN0nE", "salt length = 32"},
{"$pbkdf2-sha256$12000$0zoHwNgbIwSAkDImZGwNQUjpHcNYa43xPqd0DuH8H0OIUWqttfY.h5DynvPeG.O8N.Y$.XK4LNIeewI7w9QF5g9p5/NOYMYrApW03bcv/MaD6YQ", "salt length = 50"},
{"$pbkdf2-sha256$12000$HGPMeS9lTAkhROhd653Tuvc.ZyxFSOk9x5gTYgyBEAIAgND6PwfAmA$WdCipc7O/9tTgbpZvcz.mAkIDkdrebVKBUgGbncvoNw", "salt length = 40"},
{"$pbkdf2-sha256$12001$ay2F0No7p1QKgVAqpbQ2hg$UbKdswiLpjc5wT8Zl2M6VlE2cNiKuhAUntGciP8JjPw", "test"},
{"$pbkdf2-sha256$12000$MDEyMzQ1Njc4OTAxMjM0NTY3ODkwMTIzNDU2Nzg5MDEyMzQ1Njc4OTAxMjM0NTY3ODkw$RvyFSU8DM6qYW79urz7KPz/zzyUlHl5NlHULlsW1WKA", "51 byte salt"},
{"$pbkdf2-sha256$12000$MDEyMzQ1Njc4OTAxMjM0NTY3ODkwMTIzNDU2Nzg5MDEyMzQ1Njc4OTAxMjM0NTY3ODkwMQ$kQe4YOwY0LY5zCNNyr5UvnpeBrx/qxuIwntFnzW2zb8", "52 byte salt"},
{"$pbkdf2-sha256$12000$MDEyMzQ1Njc4OTAxMjM0NTY3ODkwMTIzNDU2Nzg5MDEyMzQ1Njc4OTAxMjM0NTY3ODkwMTIzNDU2Nzg5$QoIK6793HiOBzPq34H89QvcQDB5bksb/.7.TCLQFOeg", "60 byte salt"},
{"$pbkdf2-sha256$12000$MDEyMzQ1Njc4OTAxMjM0NTY3ODkwMTIzNDU2Nzg5MDEyMzQ1Njc4OTAxMjM0NTY3ODkwMTIzNDU2Nzg5MA$jDBOWzng7Tyk9jS0T3F/9JWhTptuRh9y./FMpIkqf3I", "61 byte salt"},
{"$pbkdf2-sha256$12000$MDEyMzQ1Njc4OTAxMjM0NTY3ODkwMTIzNDU2Nzg5MDEyMzQ1Njc4OTAxMjM0NTY3ODkwMTIzNDU2Nzg5MDE$8xnT1aRPA7r8aTZgoJqzCJxxzOZ/hn41jGAFC9nJpuU", "62 byte salt"},
{"$pbkdf2-sha256$12000$MDEyMzQ1Njc4OTAxMjM0NTY3ODkwMTIzNDU2Nzg5MDEyMzQ1Njc4OTAxMjM0NTY3ODkwMTIzNDU2Nzg5MDEyMzQ1Njc4OTAxMjM0NTY3ODkwMTIzNDU2Nzg5MDEyMzQ1Njc4OTAxMjM0NTY3ODkwMTIzNA$HZ5Vlvz/6CptMcpvAC04lRYplo8C.Roq0gi8P7Dvj8g", "115 byte salt"},
// cisco type 8 hashes.  20k iterations, different base-64 (same as WPA).  Also salt is used RAW, it is not base64 decoded prior to usage
{"$8$dsYGNam3K1SIJO$7nv/35M/qr6t.dVc7UY9zrJDWRVqncHub1PE9UlMQFs", "cisco"},
{"$8$6NHinlEjiwvb5J$RjC.H.ydVb34wDLqJvfjyG1ubxYKpfXqv.Ry9mtrNBY", "password"},
{"$8$lGO8juTOQLPCHw$cBv2WEaFCLUA24Z48CKUGixIywyGFP78r/slQcMXr3M", "JtR"},
