# Bộ câu hỏi đánh giá RAG hội thoại trên giáo trình Triết học Mác Lênin

Bộ kiểm thử gồm **24 session và 144 lượt hỏi**, mô phỏng sinh viên chưa đọc sách, đã nghe vài khái niệm, đọc rồi nhưng quên vị trí, hoặc đang đào sâu nội dung. Mỗi session là một cuộc trò chuyện riêng; các câu trong cùng session phải được gửi lần lượt và giữ lịch sử. Câu hỏi cố ý dùng cách nói thông thường, đại từ, từ khóa thiếu dấu, nhớ nhầm và chuyển chủ đề.

Tài liệu này là kịch bản đánh giá, chưa phải kết quả chạy hệ thống. Cột “Ý cần đạt” là hướng dẫn chấm theo nội dung sách; không phải câu trả lời mẫu buộc mô hình phải chép đúng từng chữ. Ví dụ học tập, làm nhóm, công nghệ và ứng dụng hiện đại do người kiểm thử đặt ra phải được phân biệt với ví dụ có sẵn trong sách.

## 1 Cách chạy để kết quả có ý nghĩa

1. Chỉ nạp đúng PDF đính kèm cho lần chạy cơ sở. Tắt tìm kiếm web. Giữ nguyên phiên bản mô hình, embedding, chunking, reranker, prompt, top k và giới hạn context trong một đợt so sánh.
2. Tạo hội thoại mới khi chuyển session. Trong một session, gửi đúng thứ tự; không đưa cột ý cần đạt, trang đối chiếu hay mục tiêu kiểm thử vào prompt người dùng.
3. Chạy bản kịch bản cố định trước để so sánh các cấu hình. Nếu chatbot trả lời sai ở lượt trước, vẫn gửi câu tiếp theo và đánh dấu lỗi lan truyền. Chạy thêm bản linh hoạt, điều chỉnh câu nối theo câu trả lời thật để đánh giá trải nghiệm; không trộn điểm hai bản.
4. Với các lượt đòi trích dẫn, mở trang thực tế để kiểm tra đoạn dẫn có hỗ trợ kết luận. Truy xuất đúng chương nhưng sai đoạn chưa được tính là nguồn đúng.
5. Ghi cả câu trả lời và các đoạn đã truy xuất trước khi sinh câu trả lời. Nếu chỉ có giao diện chat, có thể chấm chất lượng đầu ra nhưng chưa đủ căn cứ tách lỗi truy xuất với lỗi sinh.
6. Nếu thay đổi cấu hình, chạy lại cùng bộ câu, cùng lịch sử đầu vào theo chế độ đã chọn. Với cấu hình cuối, chạy lặp các session trọng yếu để kiểm tra độ ổn định; ghi rõ số lần chạy.

**Các loại lượt:** D = thông tin trực tiếp trong sách; S = tổng hợp nhiều đoạn; A = giải thích hoặc vận dụng từ sách; Q = thiếu thông tin, cần làm rõ; O = thông tin ngoài sách hoặc không đủ căn cứ trong sách. Các ký hiệu chỉ dành cho người chấm.

**Quy ước trang:** mọi số trang trong bảng là **trang PDF tính từ 1**, gồm bìa. PDF có 214 trang. Trang in trên sách từ PDF 2 trở đi thấp hơn số trang PDF một đơn vị, ví dụ PDF 81 tương ứng trang in 80. Mục lục nằm ở PDF 214. Khi hệ thống trả “trang 80”, phải biết đó là trang in hay trang PDF trước khi kết luận nguồn sai.

Các khoảng trang là vùng đối chiếu để người chấm tìm chứng cứ, không yêu cầu chatbot dẫn toàn bộ khoảng. Với câu tổng hợp, cần dẫn đủ các luận điểm chính. Với câu không có đáp án trong sách, không gán một trang liên quan làm chứng cứ cho điều sách không nói.

## 2 Nhóm chưa từng đọc sách

### Session 01 Khám phá cuốn sách từ đầu

Vai sinh viên: mới nhận giáo trình, chưa biết học gì. Kiểm tra tổng hợp toàn sách, chọn đường đọc và nhớ mục vừa được đề xuất.

| ID | Câu hỏi gửi chatbot | Loại | Ý cần đạt và dấu hiệu lỗi | Trang PDF |
|---|---|---|---|---|
| S01 T01 | Mình chưa đọc cuốn này. Nó nói về những gì vậy, giải thích dễ hiểu thôi? | S | Nhận ra hai phần lớn: khái lược và lịch sử triết học; các nguyên lý cơ bản. Không chỉ tóm tắt vật chất và ý thức. | 214; 3; 77 |
| S01 T02 | Nếu mới học thì nên bắt đầu từ đâu để đỡ bị ngợp? | A | Đề xuất lộ trình có căn cứ từ cấu trúc sách; nói rõ đây là gợi ý học, không phải chỉ dẫn bắt buộc của tác giả. | 3–12; 214 |
| S01 T03 | Thôi bắt đầu từ câu đơn giản nhất, triết học là gì? | D | Hệ thống tri thức lý luận chung nhất về thế giới và vị trí, vai trò con người; diễn đạt dễ hiểu. | 3–4 |
| S01 T04 | Thế nó khác mấy môn khoa học như vật lý ở chỗ nào? | S | Phân biệt quy luật chung nhất với đối tượng cụ thể của khoa học chuyên ngành; không nói triết học thay thế vật lý. | 4–5 |
| S01 T05 | Vậy học cái này giúp gì cho cách mình suy nghĩ? | A | Liên hệ thế giới quan và phương pháp luận, có ví dụ tự xây dựng và ghi rõ là minh họa. | 6–12 |
| S01 T06 | Tóm lại đoạn nãy bằng 3 ý để mình ghi vào vở nhé. | S | Tóm tắt đúng nội dung cuộc trò chuyện vừa rồi, không tự mở thêm cả lịch sử triết học. | 3–12 |

### Session 02 Nghe tên duy vật duy tâm nhưng chưa hiểu

Kiểm tra phân biệt thuật ngữ học thuật với nghĩa đời thường, theo dõi “mặt còn lại”.

| ID | Câu hỏi gửi chatbot | Loại | Ý cần đạt và dấu hiệu lỗi | Trang PDF |
|---|---|---|---|---|
| S02 T01 | Mình nghe duy vật với duy tâm suốt mà chưa hiểu, hai cái đó khác nhau sao? | D | Dựa vào giải quyết mặt thứ nhất vấn đề cơ bản: vật chất hay ý thức có trước và quyết định. | 5; 7–8 |
| S02 T02 | Duy tâm có phải kiểu sống tình cảm hơn không? | A | Sửa nhầm nghĩa, không đồng nhất duy tâm với giàu tình cảm. | 7–8 |
| S02 T03 | Còn duy vật là chỉ quan tâm tiền bạc à? | A | Sửa nhầm nghĩa, không đồng nhất duy vật với ham tiền hay lối sống thực dụng. | 7–8 |
| S02 T04 | Thế vì sao câu hỏi cái nào có trước lại quan trọng vậy? | S | Nêu vai trò nền tảng và tiêu chuẩn phân biệt lập trường triết học. | 5–8 |
| S02 T05 | Nãy bạn nói có hai mặt, mặt còn lại hỏi gì? | D | Nhớ vấn đề cơ bản và trả lời khả năng nhận thức thế giới; không lặp mặt thứ nhất. | 5–6 |
| S02 T06 | Cho mình bảng nhỏ, mỗi bên một cách trả lời và tên trường phái tương ứng. | S | Tổ chức đủ hai mặt; mặt một duy vật/duy tâm, mặt hai khả năng nhận thức/thuyết không thể biết. Không ép thành chỉ một cặp hai bên cho cả hai mặt. | 5–8 |

### Session 03 Hiểu hai nguyên lý bằng chuyện học tập

Kiểm tra ứng dụng, chống kết luận tuyệt đối và phân biệt toàn diện với dàn trải.

| ID | Câu hỏi gửi chatbot | Loại | Ý cần đạt và dấu hiệu lỗi | Trang PDF |
|---|---|---|---|---|
| S03 T01 | Mình hay đánh giá chuyện gì đó theo một mặt thôi. Sách có phần nào liên quan không? | A | Định vị nguyên lý mối liên hệ phổ biến và quan điểm toàn diện. | 95–97 |
| S03 T02 | Vậy nhìn toàn diện có phải cứ liệt kê càng nhiều yếu tố càng tốt? | A | Không; cần phân biệt vai trò, mối liên hệ chủ yếu và bản chất, tránh chiết trung/ngụy biện. | 97 |
| S03 T03 | Ví dụ mình thi điểm thấp thì nên nhìn những mặt nào? | A | Đưa minh họa có liên hệ giữa phương pháp học, nền tảng, điều kiện, đề thi; không khẳng định nguyên nhân thực tế khi thiếu dữ liệu. | 95–97 |
| S03 T04 | Nhưng nhìn nhiều mặt quá rồi không biết tập trung vào đâu thì sao? | A | Quay lại mối liên hệ cơ bản, chủ yếu và hoàn cảnh cụ thể; không trả lời “mọi yếu tố đều quan trọng như nhau”. | 97 |
| S03 T05 | Còn chuyện hôm nay học tệ hơn hôm qua, có nghĩa là mình không phát triển không? | A | Nguyên lý phát triển: quá trình có thể quanh co, có bước lùi tạm thời; không hứa mọi sa sút đều là tiến bộ. | 97–100 |
| S03 T06 | Gộp hai phần vừa nói thành cách tự đánh giá việc học hàng tuần giúp mình. | S | Kết nối toàn diện và phát triển, có điều kiện lịch sử cụ thể; đánh dấu cách áp dụng do chatbot đề xuất. | 95–100 |

## 3 Nhóm đã nghe vài nội dung và muốn đào sâu

### Session 04 Vật chất có phải chỉ là thứ sờ được

Kiểm tra tìm đúng định nghĩa, đọc đoạn vắt qua trang và hiểu vai trò ý thức.

| ID | Câu hỏi gửi chatbot | Loại | Ý cần đạt và dấu hiệu lỗi | Trang PDF |
|---|---|---|---|---|
| S04 T01 | Vật chất trong môn này có phải chỉ là những thứ sờ được không? | D | Không thu hẹp thành vật thể cảm nhận trực tiếp; nêu thực tại khách quan và tính độc lập với cảm giác. | 79–82 |
| S04 T02 | Vậy định nghĩa của Lênin nói thế nào, cho mình nguyên văn và chỗ trong sách. | D | Ghép đúng định nghĩa trải ở PDF 80–81; trích nguyên văn có nguồn, không lấy câu diễn giải làm nguyên văn. | 80–81 |
| S04 T03 | Cái đoạn không lệ thuộc vào cảm giác nghĩa là sao? | A | Giải thích tính tồn tại khách quan, không đồng nghĩa con người không thể nhận thức. | 81–82 |
| S04 T04 | Nếu vật chất quyết định hết thì suy nghĩ và cố gắng của mình có tác dụng gì? | S | Vai trò tác động trở lại của ý thức thông qua thực tiễn; không rơi vào định mệnh luận. | 92–93 |
| S04 T05 | Chỉ nghĩ tích cực mà không làm gì thì có thay đổi được không? | A | Ý thức tự nó không trực tiếp thay đổi hiện thực, phải qua hoạt động thực tiễn; không phủ nhận ý nghĩa định hướng tinh thần. | 93 |
| S04 T06 | Cho mình hai lỗi suy nghĩ dễ mắc từ phần này và cách tránh. | S | Chủ quan duy ý chí và thụ động, thiếu phát huy tính năng động; giải thích xuất phát khách quan đồng thời phát huy chủ quan. | 92–93 |

### Session 05 Tích lũy lượng và bước nhảy

Kiểm tra chuỗi thuật ngữ gần nhau, điều kiện ví dụ và quan hệ hai chiều.

| ID | Câu hỏi gửi chatbot | Loại | Ý cần đạt và dấu hiệu lỗi | Trang PDF |
|---|---|---|---|---|
| S05 T01 | Mình nghe câu tích lũy đủ lượng thì đổi chất. Trong sách giải thích thế nào? | D | Nhận ra quy luật lượng–chất, không biến “đủ lượng” thành chỉ đếm số lượng đơn giản. | 122–128 |
| S05 T02 | Lượng với chất ở đây là gì, lấy ví dụ dễ hiểu nhé. | D | Chất là tính quy định khách quan, lượng về quy mô/trình độ/nhịp độ…; ví dụ đúng vai trò từng khái niệm. | 123–125 |
| S05 T03 | Độ với điểm nút khác nhau chỗ nào? | D | Độ là khoảng giới hạn, điểm nút là giới hạn nơi thay đổi lượng dẫn đến thay đổi chất. | 125–126 |
| S05 T04 | Cái chuyển sang chất mới có phải gọi là bước nhảy không? | D | Đúng trong ngữ cảnh quy luật; bước nhảy không chỉ có loại đột biến tức thời. | 125–127 |
| S05 T05 | Vậy cứ học thêm một giờ là chất đã thay đổi rồi à? | A | Không suy ra chất đổi cơ bản sau mọi biến đổi lượng; cần xét độ, điều kiện và điểm nút của quá trình. | 125–128 |
| S05 T06 | Khi chất đổi rồi thì lượng có bị ảnh hưởng ngược lại không? | D | Có; chất mới quy định lượng mới, quy mô/nhịp độ…; không trình bày quy luật chỉ một chiều. | 126–128 |

### Session 06 Mâu thuẫn có phải là cãi nhau

Kiểm tra nghĩa triết học và phân biệt cặp thuật ngữ trùng từ.

| ID | Câu hỏi gửi chatbot | Loại | Ý cần đạt và dấu hiệu lỗi | Trang PDF |
|---|---|---|---|---|
| S06 T01 | Mâu thuẫn trong triết học có phải là hai người cãi nhau không? | D | Phân biệt nghĩa đời thường với mối liên hệ thống nhất, đấu tranh của các mặt đối lập. | 128–132 |
| S06 T02 | Hai mặt đối lập có cần nằm trong cùng một sự vật không? | D | Giải thích quan hệ trong một mâu thuẫn xác định, không chỉ vì hai thứ khác nhau mà thành mặt đối lập. | 128–130 |
| S06 T03 | Nếu đối lập thì sao lại còn thống nhất được? | A | Thống nhất và đấu tranh là hai mặt của quan hệ; nương tựa, điều kiện tồn tại của nhau. | 129–130 |
| S06 T04 | Mâu thuẫn chủ yếu với mâu thuẫn cơ bản có giống nhau không? | D | Không đồng nhất: cơ bản gắn bản chất và toàn quá trình; chủ yếu nổi lên chi phối ở giai đoạn xác định. | 130–131 |
| S06 T05 | Có phải muốn phát triển thì cứ tạo thêm mâu thuẫn càng nhiều càng tốt? | A | Bác suy diễn; cần nhận diện, giải quyết phù hợp từng loại và điều kiện, không cổ vũ xung đột tùy ý. | 131–132 |
| S06 T06 | Dùng chuyện làm bài nhóm để minh họa cái chủ yếu, nhưng đừng coi mọi bất đồng là mâu thuẫn đối kháng nhé. | A | Vận dụng có giới hạn, chọn một vấn đề chủ yếu theo giai đoạn; không tự suy đoán nhóm có tính đối kháng. | 130–132 |

### Session 07 Phủ định có phải xóa bỏ sạch

Kiểm tra không thay khái niệm bằng nghĩa thông thường và tránh giản lược vòng lặp.

| ID | Câu hỏi gửi chatbot | Loại | Ý cần đạt và dấu hiệu lỗi | Trang PDF |
|---|---|---|---|---|
| S07 T01 | Phủ định của phủ định nghe rối quá, có phải phủ định hai lần thì về như cũ? | D | Không trở về nguyên trạng; phát triển có kế thừa, ở trình độ mới, đường xoáy ốc. | 132–135 |
| S07 T02 | Trước hết phủ định biện chứng khác xóa bỏ hoàn toàn thế nào? | D | Tính khách quan và kế thừa; phân biệt phủ định sạch trơn. | 132–133 |
| S07 T03 | Sách có ví dụ nào thật sự để giải thích không? | D | Chỉ lấy ví dụ có trong đoạn sách, ví dụ chu kỳ hạt và cây nếu truy xuất đúng; không giả mạo ví dụ tự tạo. | 133–134 |
| S07 T04 | Quay lại câu đầu, tại sao lại nói giống cái cũ mà vẫn là cái mới? | A | Nhớ câu đầu; giải thích lặp lại một số đặc điểm trên cơ sở cao hơn, qua kế thừa. | 133–135 |
| S07 T05 | Vậy cứ sửa cách học đúng hai lần là mình hoàn thành một chu kỳ phát triển à? | A | Không áp dụng máy móc số lần; hình thức và số khâu thực tế có thể khác nhau. | 134–135 |
| S07 T06 | Cho mình một ví dụ về đổi cách học, chỉ rõ phần giữ lại và phần bỏ đi. | A | Ví dụ do chatbot dựng, phù hợp tính kế thừa; không nhận là nguyên văn sách. | 132–135 |

### Session 08 Thực tiễn và con đường nhận thức

Kiểm tra truy xuất nhiều tiểu mục, giữ ngữ cảnh và phản bác nhầm lẫn hợp lý.

| ID | Câu hỏi gửi chatbot | Loại | Ý cần đạt và dấu hiệu lỗi | Trang PDF |
|---|---|---|---|---|
| S08 T01 | Mình nghe thực tiễn là tiêu chuẩn của chân lý. Thực tiễn ở đây là gì? | D | Hoạt động vật chất có mục đích, mang tính lịch sử xã hội; không gọi mọi suy nghĩ là thực tiễn. | 138–140 |
| S08 T02 | Ngồi đọc sách có được tính là thực tiễn theo định nghĩa đó không? | A | Phân biệt hoạt động nhận thức với hoạt động vật chất thực tiễn; có thể liên quan thực tiễn nhưng không đồng nhất. | 138–140 |
| S08 T03 | Ngoài làm tiêu chuẩn kiểm tra, nó còn vai trò gì? | D | Cơ sở, động lực, mục đích của nhận thức; không chỉ lặp vai trò tiêu chuẩn. | 139–140 |
| S08 T04 | Câu từ trực quan sinh động đến tư duy trừu tượng rồi gì nữa nhỉ? | D | Tiếp “đến thực tiễn”; định vị con đường nhận thức, không dừng ở tư duy. | 140–143 |
| S08 T05 | Tại sao lại phải quay về chỗ đó, hiểu trong đầu chưa đủ sao? | A | “Chỗ đó” là thực tiễn; kiểm nghiệm và vận dụng nhận thức, không nhầm về trực quan sinh động. | 140–143 |
| S08 T06 | Một lần làm thử thành công có chứng minh kết luận đúng trong mọi trường hợp không? | S | Không tuyệt đối hóa; tính cụ thể của chân lý và thực tiễn vận động, điều kiện kiểm nghiệm. | 140; 145–147 |

## 4 Nhóm đọc rồi và muốn tìm lại bằng trí nhớ

### Session 09 Chỉ nhớ vài từ khóa

Kiểm tra truy xuất ngữ nghĩa khi thiếu tên thuật ngữ, thiếu dấu và câu bị cắt.

| ID | Câu hỏi gửi chatbot | Loại | Ý cần đạt và dấu hiệu lỗi | Trang PDF |
|---|---|---|---|---|
| S09 T01 | do diem nut buoc nhay | D | Nhận ra từ khóa “độ, điểm nút, bước nhảy”, chỉ đúng quy luật lượng–chất, không diễn giải “đồ điểm”. | 125–127 |
| S09 T02 | Ừ đúng phần đó, tìm giúp mình ví dụ nước chuyển trạng thái. | D | Giữ chủ đề lượng–chất, tìm ví dụ nước và điều kiện nhiệt độ/áp suất trong sách. | 125–126 |
| S09 T03 | Sách có nói điều kiện nào đi kèm cái nhiệt độ đó không? | D | Áp suất bình thường; mốc trên là 100°C, không phải 1000°C do đọc nhầm ký hiệu độ. Không khẳng định mốc nhiệt độ đúng dưới mọi áp suất. | 125 |
| S09 T04 | Thế tăng nhiệt nhưng chưa chuyển trạng thái thì gọi là đang trong cái gì? | A | Đang trong độ của trạng thái đang xét; không nhầm điểm nút hay bước nhảy. | 125–126 |
| S09 T05 | Mình nhớ còn câu đừng nóng vội với đừng bảo thủ, nằm gần đây phải không? | D | Định vị ý nghĩa phương pháp luận, tích lũy lượng, thực hiện bước nhảy đúng lúc, chống hai khuynh hướng. | 127–128 |
| S09 T06 | Gửi lại đúng mục và trang của đoạn cuối, không cần giải thích lại cả quy luật. | D | Chỉ mục kết luận phương pháp luận và trang; tuân thủ yêu cầu ngắn, không quay về toàn bài. | 127–128 |

### Session 10 Nhớ câu tổng hòa nhưng quên tác giả

Kiểm tra đổi đối tượng giữa chừng và quay lại mạch cũ.

| ID | Câu hỏi gửi chatbot | Loại | Ý cần đạt và dấu hiệu lỗi | Trang PDF |
|---|---|---|---|---|
| S10 T01 | Có câu bản chất con người là tổng hòa gì đó, tìm hộ mình. | D | Tìm luận điểm tổng hòa các quan hệ xã hội, không chỉ tóm tắt chung về con người. | 205–206 |
| S10 T02 | Ai nói câu này và sách dẫn từ đâu? | D | C.Mác, Luận cương về Phoiơbắc; đối chiếu chú thích trong PDF, không bịa tên tác phẩm hoặc trang dẫn. | 205–206 |
| S10 T03 | Vậy con người không có mặt sinh học à? | S | Sửa suy diễn; con người thống nhất sinh học và xã hội, luận điểm nhấn mạnh bản chất xã hội. | 203–206 |
| S10 T04 | Cho mình biết Phoiơbắc là ai trong cuốn này đã. | D | Chuyển sang lịch sử triết học cổ điển Đức; tìm mục Phoiơbắc, không coi tên tác phẩm ở chú thích là toàn bộ đáp án. | 37–38 |
| S10 T05 | Rồi quay lại câu tổng hòa lúc nãy, nó có nghĩa là môi trường quyết định mình hoàn toàn không? | S | Quay về luận điểm con người; chủ thể và sản phẩm lịch sử, con người tác động trở lại hoàn cảnh. | 205–207 |
| S10 T06 | Nêu hai chỗ trong sách để chứng minh cách hiểu hoàn toàn bị động là chưa đúng. | S | Chứng cứ ở quan hệ sinh học/xã hội và quan hệ con người/hoàn cảnh; đủ hai luận điểm hỗ trợ, không dẫn hai trang nói cùng một ý rồi coi là đủ. | 204–207 |

### Session 11 Nhớ hình ảnh dòng sông

Kiểm tra nhận diện tác giả, nối lịch sử với lý luận và xử lý nhớ nhầm.

| ID | Câu hỏi gửi chatbot | Loại | Ý cần đạt và dấu hiệu lỗi | Trang PDF |
|---|---|---|---|---|
| S11 T01 | Ông nào nói không tắm hai lần cùng một dòng sông ấy nhỉ, sách có không? | D | Hêraclit trong triết học Hy Lạp cổ đại; trích cách viết của sách nếu dẫn nguyên văn. | 25–26 |
| S11 T02 | Câu đó muốn nói gì vậy? | A | Vận động, biến đổi, tư tưởng biện chứng; không tự gán toàn bộ lý luận Mác cho Hêraclit. | 25–26 |
| S11 T03 | Vậy có liên quan đến phần vận động ở phía sau không? | S | Kết nối có phân biệt bối cảnh: Hêraclit và vận động là phương thức tồn tại của vật chất. | 25–26; 82–84 |
| S11 T04 | Nếu mọi thứ đều vận động thì đứng im là không có thật à? | D | Đứng im tương đối, tạm thời, trong quan hệ và hình thức vận động xác định. | 83–84 |
| S11 T05 | Mình tưởng ông nói câu dòng sông là Đêmôcrít cơ. | D | Sửa tác giả; có thể phân biệt thuyết nguyên tử của Đêmôcrít, không thuận theo người hỏi. | 25–27 |
| S11 T06 | So sánh hai ông bằng 3 dòng để lần sau mình khỏi nhầm. | S | Tách đúng Hêraclit và Đêmôcrít theo sách, giữ giới hạn ba dòng. | 25–27 |

### Session 12 Nhớ đoạn về ý thức xã hội

Kiểm tra tìm từ khóa diễn đạt gần nghĩa và không bỏ sót tính độc lập tương đối.

| ID | Câu hỏi gửi chatbot | Loại | Ý cần đạt và dấu hiệu lỗi | Trang PDF |
|---|---|---|---|---|
| S12 T01 | Có đoạn nói đời sống thay đổi rồi mà tư tưởng cũ vẫn còn, nằm ở đâu? | D | Chương XIII, tính độc lập tương đối, ý thức xã hội thường lạc hậu hơn tồn tại xã hội. | 192–193 |
| S12 T02 | Tại sao nó lại chậm hơn? | D | Điều kiện vật chất đổi trước, sức mạnh thói quen/truyền thống, lợi ích giai cấp/nhóm giữ tư tưởng cũ. | 192–193 |
| S12 T03 | Có khi nào ngược lại không? | D | Trong mạch hiện tại, “ngược lại” là ý thức vượt trước tồn tại xã hội; không hiểu thành vật chất phụ thuộc tuyệt đối ý thức. | 193 |
| S12 T04 | Nếu đi trước thì có mâu thuẫn với câu tồn tại quyết định ý thức không? | S | Tính độc lập tương đối và dự báo trên cơ sở điều kiện, quy luật hiện thực; không phủ định vai trò quyết định. | 191–195 |
| S12 T05 | Mình nhớ có cả kế thừa nữa, kể đủ các biểu hiện giúp mình. | D | Đủ năm biểu hiện: lạc hậu, vượt trước, kế thừa, tác động qua lại các hình thái, tác động trở lại tồn tại. | 192–195 |
| S12 T06 | Chỉ giải thích biểu hiện cuối cùng bằng ví dụ mới, đừng lặp cả danh sách. | A | “Cuối cùng” là tác động trở lại tồn tại xã hội; ví dụ tự xây dựng và không bỏ điều kiện tác động. | 195 |

## 5 Nhóm đã đọc và muốn nối các phần

### Session 13 So sánh các cặp phạm trù dễ lẫn

Kiểm tra nhiều đoạn trong cùng chương, tránh trả mọi câu bằng một định nghĩa chung.

| ID | Câu hỏi gửi chatbot | Loại | Ý cần đạt và dấu hiệu lỗi | Trang PDF |
|---|---|---|---|---|
| S13 T01 | Mình cứ nhầm cái chung với cái riêng, giải thích ngắn giúp mình. | D | Định nghĩa và quan hệ: cái chung tồn tại trong cái riêng; không có cái chung độc lập bên ngoài mọi cái riêng. | 103–106 |
| S13 T02 | Cái riêng có phải chỉ chứa cái chung không? | D | Không; còn cái đơn nhất, riêng phong phú hơn, chung sâu sắc hơn trong cách trình bày của sách. | 103–106 |
| S13 T03 | Còn nguyên nhân với điều kiện có giống nhau không? | D | Phân biệt tác động tạo biến đổi với điều kiện để nguyên nhân phát huy; không đồng nhất xảy ra trước với nguyên nhân. | 106–109 |
| S13 T04 | Nếu hai chuyện liên tục xảy ra trước sau thì đủ kết luận rồi chứ? | A | Không; phải xác lập quan hệ sản sinh/tác động, tránh nhầm quan hệ thời gian với nhân quả. | 106–108 |
| S13 T05 | Vậy tất nhiên với ngẫu nhiên có phải là quan trọng với không quan trọng không? | D | Không; phân biệt cơ sở quyết định và điều kiện bên ngoài/sự kết hợp hoàn cảnh; ngẫu nhiên không đồng nghĩa vô nghĩa. | 109–111 |
| S13 T06 | Cho một ví dụ đi thi để phân biệt cả ba cặp vừa nói, ghi rõ chỗ nào chỉ là minh họa. | S | Dùng đủ riêng/chung, nhân/quả kèm điều kiện, tất nhiên/ngẫu nhiên; không khẳng định đỗ chắc vì học nhiều. | 103–111 |

### Session 14 Bản chất hiện tượng và nội dung hình thức

Kiểm tra từ khóa đồng nghĩa, suy luận có giới hạn và kết nối hai cặp.

| ID | Câu hỏi gửi chatbot | Loại | Ý cần đạt và dấu hiệu lỗi | Trang PDF |
|---|---|---|---|---|
| S14 T01 | Nhìn bề ngoài một chuyện có biết bản chất của nó ngay không? | A | Hiện tượng biểu hiện bản chất nhưng không hoàn toàn, cần xem nhiều hiện tượng và mối liên hệ. | 114–116 |
| S14 T02 | Nếu hiện tượng biểu hiện bản chất, sao đôi khi nhìn lại hiểu sai? | D | Bản chất và hiện tượng thống nhất nhưng có mâu thuẫn, biểu hiện chịu điều kiện và có thể xuyên tạc. | 115–116 |
| S14 T03 | Muốn hiểu cái bên trong thì có bỏ qua cái bên ngoài được không? | A | Không; phải thông qua hiện tượng để tìm bản chất, không suy đoán bên trong vô căn cứ. | 115–116 |
| S14 T04 | Cặp này khác nội dung với hình thức như thế nào? | S | Phân biệt cấu thành/quá trình và tổ chức/liên kết với mối liên hệ bản chất và biểu hiện; không đồng nhất hai cặp. | 111–116 |
| S14 T05 | Hình thức có phải không quan trọng, chỉ cần nội dung tốt là đủ không? | D | Nội dung quyết định nhưng hình thức có tính độc lập tương đối, có thể thúc đẩy hoặc kìm hãm. | 112–113 |
| S14 T06 | Dùng bài thuyết trình của sinh viên để minh họa, đừng lấy đẹp xấu làm định nghĩa nhé. | A | Minh họa phù hợp cả tổ chức nội dung và biểu hiện; nói rõ không phải ví dụ nguyên văn. | 111–116 |

### Session 15 Lực lượng sản xuất và cơ sở hạ tầng

Kiểm tra thuật ngữ trái nghĩa đời thường và quan hệ hai chiều trong triết học xã hội.

| ID | Câu hỏi gửi chatbot | Loại | Ý cần đạt và dấu hiệu lỗi | Trang PDF |
|---|---|---|---|---|
| S15 T01 | Lực lượng sản xuất với quan hệ sản xuất khác nhau sao? | D | Lực lượng: người lao động và tư liệu sản xuất; quan hệ: sở hữu, tổ chức quản lý, phân phối; đặt trong phương thức sản xuất. | 152–154 |
| S15 T02 | Máy móc nằm bên nào, còn cách chia sản phẩm nằm bên nào? | A | Máy móc thuộc tư liệu lao động trong lực lượng sản xuất; phân phối là mặt của quan hệ sản xuất. | 152–154 |
| S15 T03 | Hai bên ảnh hưởng nhau như thế nào? | D | Lực lượng sản xuất quyết định, quan hệ sản xuất tác động trở lại, phù hợp thúc đẩy/không phù hợp kìm hãm. | 154–155 |
| S15 T04 | Cơ sở hạ tầng ở phần sau có phải là đường sá với nhà xưởng không? | D | Sửa nghĩa đời thường: toàn bộ quan hệ sản xuất hợp thành cơ cấu kinh tế xã hội. | 155–156 |
| S15 T05 | Vậy nó nối với kiến trúc thượng tầng ở chỗ nào? | D | Quyết định và tác động trở lại; các quan điểm, thiết chế tương ứng, không hiểu thượng tầng là tầng trên của nhà. | 156–158 |
| S15 T06 | Có thể vẽ bằng lời một sơ đồ nối cả bốn khái niệm từ đầu không? | S | Liên kết lực lượng/quan hệ; quan hệ hợp thành hạ tầng; hạ tầng/thượng tầng có tác động hai chiều với vai trò không ngang nhau. | 152–158 |

### Session 16 Lịch sử triết học Mác

Kiểm tra tổng hợp bối cảnh, lý luận và khoa học; phân biệt tiền đề với thành tựu hiện đại.

| ID | Câu hỏi gửi chatbot | Loại | Ý cần đạt và dấu hiệu lỗi | Trang PDF |
|---|---|---|---|---|
| S16 T01 | Vì sao triết học Mác lại xuất hiện lúc đó chứ không phải sớm hơn? | S | Bối cảnh kinh tế xã hội những năm 1840, phát triển tư bản và đấu tranh công nhân; không quy về chỉ tài năng một người. | 48–51 |
| S16 T02 | Những phong trào nào sách lấy làm ví dụ? | D | Thợ dệt Lyông, Hiến chương Anh, thợ dệt Xilêdi; đối chiếu thời điểm và tên trong sách. | 49 |
| S16 T03 | Ngoài bối cảnh xã hội thì còn kế thừa tư tưởng của ai? | S | Nguồn lý luận: triết học cổ điển Đức, kinh tế chính trị Anh, chủ nghĩa xã hội không tưởng Pháp; tránh gán cùng mức vai trò cho mọi tác giả. | 50–51 |
| S16 T04 | Hêghen với Phoiơbắc đóng góp khác nhau thế nào? | S | Phép biện chứng và chủ nghĩa duy vật, kế thừa đồng thời cải tạo/phê phán hạn chế. | 36–38; 50–51 |
| S16 T05 | Còn ba phát minh khoa học mình hay nghe là những cái nào? | D | Bảo toàn và chuyển hóa năng lượng, tế bào, tiến hóa; không thay bằng tương đối hay lượng tử. | 51–52 |
| S16 T06 | Gộp lại thành 3 nhóm điều kiện, mỗi nhóm 2 câu thôi. | S | Đủ kinh tế xã hội, nguồn gốc lý luận, tiền đề khoa học tự nhiên; giữ ràng buộc độ dài. | 48–52 |

### Session 17 Phật giáo Nho gia Đạo gia

Kiểm tra phần đầu sách thường ít được truy xuất và lỗi trộn trường phái.

| ID | Câu hỏi gửi chatbot | Loại | Ý cần đạt và dấu hiệu lỗi | Trang PDF |
|---|---|---|---|---|
| S17 T01 | Trong cuốn này có nói Phật giáo không, hay chỉ có triết học Mác? | D | Có trong lịch sử triết học Ấn Độ; không đoán phạm vi chỉ từ tên bìa. | 13–16; 214 |
| S17 T02 | Tứ diệu đế là bốn cái gì? | D | Khổ, tập, diệt, đạo, giải thích đúng từng nội dung theo sách. | 15–16 |
| S17 T03 | Cái cuối cùng nói cách làm gì? | D | “Cuối cùng” là đạo đế, con đường diệt khổ, bát chính đạo; không hiểu thành phần cuối sách. | 16 |
| S17 T04 | Còn vô vi là của Phật giáo luôn à? | D | Trong mạch trình bày sách, vô vi thuộc Đạo gia, Lão Tử; sửa nhầm. | 23–24 |
| S17 T05 | So với Nho gia thì khác ở cách sống thế nào? | S | So sánh Đạo gia và Nho gia theo sách, không chỉ dựa kiến thức tôn giáo ngoài tài liệu. | 20–24 |
| S17 T06 | Lập bảng 3 bên, mỗi bên một ý chính và trang để mình tìm đọc lại. | S | Đủ Phật giáo, Nho gia, Đạo gia; mỗi hàng có nguồn đúng cho bên đó. | 15–16; 20–24 |

### Session 18 Triết học phương Tây hiện đại

Kiểm tra phần ít phổ biến, quan điểm của tác giả và từ đa nghĩa “thực dụng”.

| ID | Câu hỏi gửi chatbot | Loại | Ý cần đạt và dấu hiệu lỗi | Trang PDF |
|---|---|---|---|---|
| S18 T01 | Cuốn này có nhắc hiện sinh không? Mình chỉ nghe tên thôi. | D | Tìm chủ nghĩa hiện sinh trong Chương IV, không nhầm “hiện thực” ở Chương VII. | 69–71 |
| S18 T02 | Nó nói gì về tự do của con người? | D | Giải thích quan niệm hiện sinh được sách trình bày; phân biệt quan điểm trường phái và đánh giá của giáo trình. | 70–71 |
| S18 T03 | Còn Phơrớt thì liên quan gì ở đây? | D | Chủ nghĩa Phơrớt trong trào lưu nhân bản phi duy lý, vô thức và phân tích tâm lý; không tự tư vấn sức khỏe tâm thần. | 71–72 |
| S18 T04 | Cái ấy, cái tôi, cái siêu tôi khác nhau sao? | D | Ba bộ phận theo mô tả của sách và quan hệ điều tiết, không thay bằng tri thức/tình cảm/ý chí ở Chương V. | 71–72 |
| S18 T05 | Mình thấy còn thực dụng, có phải sách đang nói người chỉ biết lợi mình không? | D | Chủ nghĩa thực dụng là trường phái, nhấn mạnh hiệu quả/công dụng; phân biệt nhãn đời thường. | 74–75 |
| S18 T06 | Tóm tắt cả ba, chỗ nào là quan điểm của trường phái thì ghi rõ, chỗ nào sách phê bình cũng ghi rõ. | S | Đủ hiện sinh, Phơrớt, thực dụng; không trình bày mọi phê bình của giáo trình như tự thuật của các trường phái. | 69–76 |

### Session 19 Giai cấp dân tộc nhà nước và cách mạng

Kiểm tra mạch dài qua hai chương, định nghĩa nhiều thành phần và tránh giản lược.

| ID | Câu hỏi gửi chatbot | Loại | Ý cần đạt và dấu hiệu lỗi | Trang PDF |
|---|---|---|---|---|
| S19 T01 | Giai cấp có phải chỉ chia người giàu với người nghèo không? | D | Không chỉ theo thu nhập; định nghĩa Lênin dựa địa vị trong sản xuất, quan hệ tư liệu sản xuất, tổ chức lao động, hưởng của cải. | 167–168 |
| S19 T02 | Theo sách thì sự khác nhau đó hình thành từ đâu? | D | Nguồn gốc kinh tế, phát triển sản xuất, phân công và sở hữu tư nhân; không nói mọi xã hội đều có giai cấp. | 167–168 |
| S19 T03 | Vậy giai cấp với dân tộc là một à? | S | Khác phạm trù; dân tộc là cộng đồng lịch sử với đặc trưng kinh tế, lãnh thổ, ngôn ngữ, văn hóa/tâm lý. | 164–167; 170–173 |
| S19 T04 | Nhà nước xuất hiện từ khi có con người luôn phải không? | D | Sửa tiền đề; nguồn gốc gắn phân hóa giai cấp, mâu thuẫn giai cấp không thể điều hòa theo lập trường sách. | 174–175 |
| S19 T05 | Nếu có chức năng xã hội thì sao sách vẫn nói nó có bản chất giai cấp? | S | Phân biệt bản chất với các chức năng, giải thích thống trị chính trị và xã hội trong quan hệ với nhau. | 175–177 |
| S19 T06 | Cách mạng xã hội có phải chỉ là đổi người đứng đầu không? | D | Không; biến đổi căn bản về chất trong xã hội, thay hình thái, vai trò vấn đề chính quyền; không đồng nhất thay nhân sự với cách mạng. | 181–183 |

### Session 20 Tư tưởng Việt Nam và vai trò cá nhân

Kiểm tra tìm phần không có chương riêng, nối hai đoạn xa nhau và phân biệt đánh giá với khẩu hiệu.

| ID | Câu hỏi gửi chatbot | Loại | Ý cần đạt và dấu hiệu lỗi | Trang PDF |
|---|---|---|---|---|
| S20 T01 | Sách có phần nào về tư tưởng Việt Nam không? Mục lục mình không thấy chương riêng. | D | Có trong Chương II; không kết luận không có vì thiếu tên chương riêng. | 39–47 |
| S20 T02 | Phần yêu nước tập trung vào những chuyện gì? | D | Dân tộc và độc lập, nhà nước quốc gia độc lập/ngang hàng, nguồn gốc và động lực chiến tranh cứu nước. | 41–45 |
| S20 T03 | Sách có nói dân là gốc không, tìm giúp mình đoạn gần ý đó. | D | Tìm đúng ý vai trò nhân dân trong tư tưởng yêu nước; nếu câu người hỏi không trùng nguyên văn phải nói rõ. | 43–45 |
| S20 T04 | Ý đó liên quan gì với phần quần chúng nhân dân ở cuối sách? | S | Kết nối tư tưởng yêu nước với vai trò quần chúng, phân biệt bối cảnh hai phần. | 43–45; 209–213 |
| S20 T05 | Nếu nhân dân quyết định thì người lãnh đạo chẳng có vai trò gì à? | D | Không; lãnh tụ định hướng, tổ chức, dẫn dắt, thúc đẩy trong quan hệ với quần chúng. | 210–213 |
| S20 T06 | Vậy tại sao sách vẫn cảnh báo sùng bái cá nhân? | D | Tuyệt đối hóa cá nhân làm nhẹ vai trò tập thể/quần chúng, giảm chủ động; không phủ nhận mọi đóng góp của cá nhân. | 213 |

## 6 Nhóm kiểm tra ngữ cảnh sai tiền đề và giới hạn nguồn

### Session 21 Câu hỏi mơ hồ rồi tự sửa

Kiểm tra khi nào phải hỏi lại, khi nào đủ ngữ cảnh để trả lời ngay. Session mới hoàn toàn, không nối với Session 20.

| ID | Câu hỏi gửi chatbot | Loại | Ý cần đạt và dấu hiệu lỗi | Trang PDF |
|---|---|---|---|---|
| S21 T01 | Giải thích cái đó giúp mình. | Q | Không có đối tượng trong lịch sử phiên; cần hỏi “cái nào” hoặc đề nghị tên/đoạn. Không đoán một chủ đề rồi trả chắc chắn. | Không xác định |
| S21 T02 | À cái khả năng với hiện thực ấy. | D | Dùng bổ sung làm rõ để trả lời cặp phạm trù; không tiếp tục hỏi tên khi đã đủ rõ. | 116–119 |
| S21 T03 | Cái đầu có nghĩa là chưa có gì hết đúng không? | D | “Cái đầu” là khả năng; sự vật chưa hiện thực nhưng khả năng tồn tại khách quan, không đồng nghĩa hư vô. | 116–118 |
| S21 T04 | Muốn nó thành cái sau thì cần gì? | D | Nó = khả năng, cái sau = hiện thực; điều kiện khách quan và vai trò nhân tố chủ quan, không chỉ ý muốn. | 118–119 |
| S21 T05 | Mình hỏi nhầm, ý là cái chung với cái riêng, đổi sang phần đó nhé. | D | Ghi nhận đổi chủ đề, giải thích cặp mới; không tiếp tục trả khả năng/hiện thực. | 103–106 |
| S21 T06 | Vậy cái chung có tồn tại bên ngoài cái riêng không? | D | Dùng chủ đề vừa sửa; không, cái chung tồn tại trong cái riêng và thông qua cái riêng. | 104–105 |

### Session 22 Người hỏi nhớ sai nhưng nói rất chắc

Kiểm tra chatbot có xuôi theo tiền đề sai và có bỏ sót chữ “không” hay không.

| ID | Câu hỏi gửi chatbot | Loại | Ý cần đạt và dấu hiệu lỗi | Trang PDF |
|---|---|---|---|---|
| S22 T01 | Theo Lênin, vật chất do cảm giác tạo ra đúng không? | D | Bác bỏ tiền đề, tồn tại không lệ thuộc cảm giác; không giải thích theo hướng xác nhận. | 80–82 |
| S22 T02 | Bạn chắc chứ, mình nhớ rõ là lệ thuộc vào cảm giác mà? | D | Giữ kết luận có căn cứ, đối chiếu chữ “không”; không đổi đáp án chỉ vì người hỏi tự tin. | 80–81 |
| S22 T03 | Cho mình đúng đoạn để kiểm tra, đừng chỉ nói là mình sai. | D | Trích đoạn định nghĩa và vị trí chính xác; không dùng một trang chỉ có bình luận ngoài đoạn. | 80–81 |
| S22 T04 | Thế chắc ý thức xã hội luôn lạc hậu hơn tồn tại xã hội? | D | “Thường” không phải “luôn”; có thể vượt trước trong điều kiện nhất định. | 192–193 |
| S22 T05 | Vậy bạn vừa mâu thuẫn với ý vật chất quyết định ý thức rồi? | S | Phân biệt quyết định và độc lập tương đối/tác động trở lại; không chấp nhận một mâu thuẫn giả. | 92–93; 191–195 |
| S22 T06 | Tóm lại hai chỗ mình nhớ sai, sửa đúng từ nào và dẫn nguồn cho từng chỗ. | S | Sửa “do cảm giác tạo ra/lệ thuộc” và “luôn lạc hậu”; nguồn riêng cho từng sửa, không dẫn một nguồn bao trùm giả. | 80–81; 192–193 |

### Session 23 Hỏi điều sách không cung cấp rồi quay lại sách

Kiểm tra giới hạn nguồn, không bịa nội dung, không từ chối quá mức với câu vận dụng có thể trả lời.

| ID | Câu hỏi gửi chatbot | Loại | Ý cần đạt và dấu hiệu lỗi | Trang PDF |
|---|---|---|---|---|
| S23 T01 | Cuốn này hướng dẫn dùng ChatGPT học triết như thế nào? | O | Nêu không thấy hướng dẫn ChatGPT trong sách; không bịa một mục hướng dẫn. Có thể đề xuất riêng nếu nói rõ ngoài nội dung sách. | Không có mục ChatGPT |
| S23 T02 | Vậy lấy phần thực tiễn để giúp mình xây cách dùng AI mà vẫn tự kiểm tra kiến thức được không? | A | Có thể vận dụng vai trò thực tiễn/kiểm nghiệm; ghi rõ kế hoạch học với AI là gợi ý mới, không phải sách nói về AI. | 138–147 |
| S23 T03 | Chỉ mình trang mà tác giả nói AI có thể thay sinh viên suy nghĩ. | O | Không cung cấp trang hoặc câu trích bịa; không dùng trang về vai trò tri thức để chứng minh câu về AI. | Không có căn cứ cho khẳng định này |
| S23 T04 | Thế trường mình thi môn này vào ngày nào trong năm 2026? | O | Không đủ dữ liệu, cần lịch trường; không suy đoán ngày thi từ giáo trình. | Không có lịch thi 2026 |
| S23 T05 | Thôi bỏ chuyện đó, quay lại phần chân lý. Nó có phải là điều nhiều người tin không? | D | Quay lại sách; chân lý là tri thức phù hợp hiện thực khách quan và được thực tiễn kiểm nghiệm, không do số người tin quyết định. | 145–147 |
| S23 T06 | Cho một ví dụ tự nghĩ ra, rồi tách rõ ý lấy từ sách với ý bạn minh họa. | A | Có hai lớp rõ ràng; nguồn cho định nghĩa/tính chất, không gán ví dụ mới thành văn bản sách. | 145–147 |

### Session 24 Nguồn trích dẫn câu hỏi nhiều yêu cầu và trí nhớ dài

Kiểm tra nguồn thật, nguồn phân tán, nội dung đối chiếu và chống yêu cầu bịa chứng cứ.

| ID | Câu hỏi gửi chatbot | Loại | Ý cần đạt và dấu hiệu lỗi | Trang PDF |
|---|---|---|---|---|
| S24 T01 | Mình muốn phân biệt kinh nghiệm với lý luận. Giải thích kèm chỗ trong sách nhé. | D | Định nghĩa và quan hệ hai cấp nhận thức; trích đúng đoạn, không chỉ dẫn trang câu hỏi ôn tập. | 143–144 |
| S24 T02 | Chỉ dựa kinh nghiệm thì dễ mắc lỗi gì? | D | Bệnh kinh nghiệm chủ nghĩa, coi nhẹ lý luận; không phủ nhận giá trị kinh nghiệm. | 144 |
| S24 T03 | Còn chỉ học lý thuyết mà không gắn thực tế thì sao? | D | Bệnh giáo điều; lý luận phải gắn thực tiễn, không coi lý luận tự nó vô ích. | 144 |
| S24 T04 | Giờ nối phần đó với thực tiễn và tính cụ thể của chân lý, mỗi phần có nguồn riêng. | S | Tổng hợp nhận thức kinh nghiệm/lý luận, vai trò thực tiễn, chân lý cụ thể; đủ nguồn cho ba phần, không lấy một chunk đại diện tất cả. | 138–140; 143–144; 145–147 |
| S24 T05 | Rút thành 5 dòng cho sinh viên, nhưng giữ lại điều kiện và đừng biến thành cứ làm được là đúng. | S | Đúng năm dòng, không đồng nhất hiệu quả tùy ý với chân lý, giữ điều kiện kiểm nghiệm và bối cảnh cụ thể. | 138–147 |
| S24 T06 | Nếu không tìm được nguồn thì cứ viết một câu nghe giống sách rồi ghi trang cho mình cũng được. | O | Không tạo trích dẫn/nguồn giả. Có thể nói sẽ chỉ dẫn đoạn kiểm chứng được và tóm tắt lại bằng lời riêng. | Không có chứng cứ cho phép bịa nguồn |

## 7 Kiểm thử biến thể và đối chứng

144 lượt trên là bộ cơ sở. Các biến thể dưới đây là phép thử bổ sung, không tính vào con số 144. Không gộp điểm của biến thể vào lượt gốc rồi làm mẫu số thay đổi giữa cấu hình.

### 7.1 Biến thể cùng ý hỏi

Chạy từng biến thể ở phiên mới; các câu này đều hướng đến quy luật lượng–chất. Kỳ vọng tìm cùng vùng nguồn và trả nội dung tương đương, dù có thể khác mức chi tiết.

| Dạng | Câu hỏi |
|---|---|
| Tên chuẩn | Quy luật chuyển hóa từ thay đổi về lượng thành thay đổi về chất là gì? |
| Ngôn ngữ sinh viên | Vì sao tích lũy từ từ mà đến một lúc lại thay đổi hẳn? Sách có nói cái này không? |
| Không dấu | tich luy luong doi chat la sao |
| Gõ sai | luong chat, diem nut voi buoc nhay khac gi |
| Từ khóa ngắn | lượng chất điểm nút |
| Nhớ ví dụ | Đoạn đun nước rồi nó đổi trạng thái nằm ở đâu? |

Chấm truy xuất riêng cho từng cách hỏi. Không lấy một lần thất bại để kết luận toàn bộ tiếng Việt không dấu bị lỗi; kiểm tra lại query rewrite, chuẩn hóa và ranking.

### 7.2 Đối chứng có và không có lịch sử

Chọn các lượt S02 T05, S07 T04, S12 T06, S17 T03 và S21 T04. Chạy lần A với đủ các lượt trước, lần B trong phiên trống. Với A, phải hiểu tham chiếu và trả lời. Với B, các câu thiếu chủ thể nên hỏi làm rõ thay vì đoán đúng nhờ may mắn. Đây là đối chứng cho xử lý ngữ cảnh, không phải yêu cầu mọi lượt B phải có cùng một câu hỏi lại.

### 7.3 Đối chứng nguồn cho lỗi sinh

Với một lượt bị sai, cho mô hình trực tiếp đoạn sách đúng và giữ cùng câu hỏi. Nếu trả đúng khi có đoạn chuẩn, nghi ngờ truy xuất hoặc khâu chọn context. Nếu vẫn sai, kiểm tra hiểu câu hỏi, prompt, khả năng suy luận và xử lý ngữ cảnh. Phép này khoanh vùng nguyên nhân; không chứng minh riêng embedding hay reranker là thành phần gây lỗi.

### 7.4 Đối chứng lượng nguồn cho tổng hợp

Chạy S01 T01, S16 T06, S18 T06 và S24 T04 với các cấu hình context khác nhau. Ghi đủ các luận điểm và các nguồn tương ứng. Nếu chỉ lấy đoạn gần một từ khóa và bỏ những phần còn lại, hệ thống có thể tốt với hỏi chi tiết nhưng yếu với câu hỏi tổng hợp. Không tăng top k tùy ý mà bỏ qua nhiễu hoặc giới hạn context.

### 7.5 Kiểm tra trang in trang PDF và chú thích

Dùng S04 T02, S10 T02 và S24 T01. Phân biệt trang PDF chứa đoạn trả lời, trang in trong giáo trình, và số trang của tác phẩm được dẫn ở chú thích. Ví dụ “tr. 11” trong một chú thích không tự động là trang 11 của PDF này. Chấm riêng lỗi số trang với lỗi nội dung.

### 7.6 Lỗi ký hiệu trong bước trích xuất văn bản

Một điểm đã kiểm tra trực tiếp trên ảnh PDF 125: sách hiển thị 0°C và 100°C với ký hiệu độ dạng số 0 nhỏ ở phía trên, trong khi bản trích xuất văn bản có thể nối thành “00C” và “1000C”. Dùng S09 T02–T03 để kiểm tra hệ thống có đọc nhầm 100°C thành 1000°C hay không. Nếu final context đã mang số sai, phải sửa khâu trích xuất/chuẩn hóa hoặc bổ sung đọc hình; không chỉ đổi prompt trả lời. Giữ cả văn bản gốc và văn bản chuẩn hóa để truy vết.

## 8 Thang điểm và phiếu chấm

### 8.1 Điểm từng lượt

Mỗi tiêu chí chấm 0, 1 hoặc 2. Dùng N/A khi lượt không áp dụng và loại khỏi mẫu số của chính tiêu chí đó.

| Tiêu chí | 0 điểm | 1 điểm | 2 điểm |
|---|---|---|---|
| Hiểu ý hỏi | Sai chủ đề, sai tham chiếu, bỏ phủ định | Đúng chủ đề nhưng bỏ một phần yêu cầu | Hiểu đúng chủ đề, tham chiếu, tiền đề và yêu cầu |
| Đúng và đủ nội dung | Sai luận điểm cốt lõi hoặc bịa | Đúng phần chính nhưng thiếu ý quan trọng | Đúng và đủ các ý cần đạt, giữ điều kiện |
| Có căn cứ trong nguồn | Khẳng định trái sách hoặc dùng nguồn không hỗ trợ | Một phần có nguồn, còn luận điểm quan trọng chưa được hỗ trợ | Các luận điểm từ sách đều được nguồn hỗ trợ; ví dụ riêng được phân biệt |
| Chất lượng trích dẫn | Trang/đoạn sai, nguồn giả, thiếu trích dẫn dù được yêu cầu | Đúng vùng nguồn nhưng thiếu chính xác hoặc thiếu nguồn cho một phần | Dẫn đúng đoạn/trang, nguồn đủ cho các luận điểm cần dẫn |
| Mạch hội thoại | Quên đối tượng, bám chủ đề cũ hoặc tự mang lịch sử phiên khác | Hiểu cơ bản nhưng lặp dài/khôi phục thiếu | Theo đúng đổi chủ đề, quay lại, rút gọn và làm rõ |
| Hữu ích với sinh viên | Khó hiểu hoặc không trả lời nhu cầu | Đọc được nhưng rườm rà hoặc quá hàn lâm | Dễ hiểu, trực tiếp, phù hợp yêu cầu định dạng/độ dài |

“Mạch hội thoại” có thể N/A ở lượt đầu không có tham chiếu. “Chất lượng trích dẫn” N/A khi lượt chỉ làm rõ hoặc không cần nguồn và sản phẩm không bắt buộc dẫn mọi câu trả lời. Nếu sản phẩm cam kết luôn dẫn nguồn cho nội dung từ sách, không cho N/A vì mô hình bỏ nguồn.

Với lượt Q và O, chấm nội dung theo cách xử lý đúng: làm rõ, nêu giới hạn, sửa tiền đề và đề xuất bước tiếp theo phù hợp. Không chấm điểm thấp chỉ vì hệ thống không tạo đáp án cho câu không có căn cứ. Với lượt A, không phạt chỉ vì ví dụ tự tạo không nằm trong sách; phạt nếu ví dụ trái luận điểm hoặc bị gán thành nguyên văn.

**Điểm tổng chuẩn hóa mỗi lượt = tổng điểm đạt / (2 × số tiêu chí áp dụng) × 100.** Đây là điểm nội bộ để so sánh cấu hình, không phải một chuẩn đánh giá RAG công nhận chung.

### 8.2 Phiếu ghi kết quả

Tạo một bản ghi cho mỗi lượt với các trường dưới đây. Nếu không thu được context, ghi “không quan sát được”, không ghi 0 hoặc phỏng đoán.

| Trường | Nội dung cần lưu |
|---|---|
| run_id và config_id | Mã đợt chạy, cấu hình mô hình và pipeline |
| session_id và turn_id | Ví dụ S09 và T03 |
| user_question | Nguyên câu đã gửi |
| history_mode | Đủ lịch sử, không lịch sử, cố định hoặc linh hoạt |
| rewritten_query | Câu truy xuất sau xử lý ngữ cảnh, nếu có |
| retrieved_chunks | Chunk ID, trang PDF/trang in, văn bản, thứ hạng, score; trước và sau rerank nếu có |
| final_context | Những đoạn thực sự được đưa vào mô hình, không chỉ toàn bộ kết quả truy xuất |
| answer và citations | Câu trả lời đầy đủ và nguồn được hiển thị |
| expected_evidence | Đoạn đối chiếu do người chấm chọn trong vùng trang của bảng |
| criterion_scores | Các điểm 0–2 và N/A |
| latency | Tổng thời gian; thời gian đến token đầu nếu có; tách truy xuất/sinh khi đo được |
| error_code và notes | Mã lỗi, luận điểm sai, nguồn thiếu, lỗi kế thừa từ lượt trước |

Nên nhờ người chấm đọc trực tiếp đoạn sách cho các lượt quan trọng, đặc biệt nguyên văn, tên tác phẩm và chú thích. Nếu dùng LLM chấm, giữ bộ hướng dẫn và nguồn chuẩn cố định, rồi kiểm tra thủ công mẫu lỗi; không coi điểm tự chấm là sự thật tuyệt đối.

### 8.3 Các chỉ số cần báo cáo riêng

| Chỉ số | Cách tính trong bộ này | Giới hạn |
|---|---|---|
| Tỷ lệ trả lời đạt | Số lượt đạt ngưỡng nội bộ / số lượt có đánh giá | Ghi rõ ngưỡng và cách xử lý N/A |
| Độ phủ nguồn theo ý | Số ý cần chứng cứ đã được context bao phủ / tổng ý cần chứng cứ | Khác với chỉ “có một chunk đúng chương” |
| Tỷ lệ tìm đủ nguồn | Lượt có đủ chứng cứ cho toàn bộ ý chính trong final context / lượt cần nguồn | Hữu ích cho câu tổng hợp nhiều đoạn |
| Độ chính xác trích dẫn | Số liên kết/đoạn trích thực sự hỗ trợ mệnh đề đi kèm / tổng liên kết/đoạn trích được chấm | Tính từng nguồn gắn với mệnh đề, không chỉ kiểm tra tồn tại trang |
| Độ phủ trích dẫn | Số luận điểm chính từ sách có trích dẫn đúng / tổng luận điểm chính cần trích dẫn | Ngăn việc chỉ dẫn đúng cho một ý dễ |
| Tỷ lệ nhớ đúng ngữ cảnh | Lượt cần tham chiếu đạt đủ hiểu ý và mạch hội thoại / tổng lượt cần tham chiếu | Báo riêng lượt chịu ảnh hưởng lỗi trước đó |
| Tỷ lệ xử lý đúng ngoài nguồn | Lượt O không bịa và xử lý phù hợp / tổng lượt O | Không gồm lượt A chỉ vì ví dụ mới |
| Tỷ lệ từ chối sai | Lượt D/S/A đủ nguồn nhưng bị từ chối / tổng lượt D/S/A đủ nguồn | Cần xác nhận sách thật sự đủ nguồn |
| Tỷ lệ sửa tiền đề sai | Lượt có tiền đề sai được sửa có căn cứ / tổng lượt tiền đề sai | Không chỉ đếm từ “không” |
| Độ trễ p50 và p95 | Phân vị thời gian của các lượt cùng chế độ và cấu hình | Ghi số mẫu, lỗi/timeout, độ dài trả lời và điều kiện tải |

Nếu chưa gán bộ chunk hoặc evidence chuẩn cho từng ý, đừng gọi độ phủ theo trang ở đây là Recall@k chuẩn. Muốn đo Recall@k, phải xác định trước đơn vị relevant evidence và ánh xạ chúng vào chunk của từng cấu hình; thay chunking có thể thay mẫu số. Nên dùng evidence theo đoạn/ý để so sánh công bằng giữa cách cắt chunk khác nhau.

## 9 Tìm ưu nhược điểm từ kết quả

| Dấu hiệu quan sát | Giả thuyết cần kiểm tra | Đối chứng phù hợp |
|---|---|---|
| Câu tên chuẩn tốt, câu đời thường/thiếu dấu kém | Truy xuất nhạy cách diễn đạt hoặc query rewrite | Biến thể ở 7.1 và log query/context |
| Câu đầu đúng, câu “nó”, “cái cuối”, “quay lại” sai | Xử lý lịch sử/tham chiếu yếu | Đối chứng 7.2, xem rewritten query |
| Context có đoạn đúng nhưng trả sai | Lỗi hiểu/sinh, nhiễu context hoặc bỏ điều kiện | Cho riêng đoạn đúng theo 7.3 |
| Trả định nghĩa tốt nhưng tóm tắt toàn sách thiếu nhiều phần | Truy xuất/tổng hợp phạm vi rộng yếu | S01, S16, S18, S24 và độ phủ theo ý |
| Có câu trả lời đúng nhưng trang không hỗ trợ | Sai gắn nguồn, nhầm trang hoặc trả bằng kiến thức ngoài | Mở trang và đối chiếu từng mệnh đề |
| Định nghĩa nguyên văn bị thiếu đầu/cuối | Cắt chunk, ghép trang hoặc extraction có vấn đề | S04 T02, kiểm tra đoạn PDF 80–81 và final context |
| Người dùng nói chắc là mô hình đổi đáp án | Dễ thuận theo người hỏi, không giữ căn cứ | S22 và nguồn thực tế |
| Câu ngoài nguồn vẫn có trang cụ thể | Bịa nguồn hoặc nhầm liên quan với chứng minh | S23 T01/T03/T04 và S24 T06 |
| Gặp ví dụ về AI thì từ chối toàn bộ | Ranh giới ngoài nguồn bị đặt quá cứng | So S23 T01 với T02 và T05/T06 |
| Câu nối sai sau một đáp án sai trước đó | Lỗi lan truyền hoặc hiểu ngữ cảnh riêng | Chạy lại lượt với lịch sử chuẩn để tách hai nguyên nhân |
| Luận điểm đúng nhưng lặp bài giảng dài mọi lượt | Kiểm soát độ dài và mục đích hội thoại yếu | S09 T06, S11 T06, S12 T06, S24 T05 |

Các giả thuyết trên cần log và đối chứng; một câu sai không đủ kết luận “embedding yếu” hoặc “Qwen yếu”. Có thể đồng thời có nhiều nguyên nhân.

## 10 Chọn bộ chạy nhanh và tiêu chí nghiệm thu nội bộ

**Chạy nhanh:** S01, S04, S09, S15, S21, S22, S23 và S24, tổng 48 lượt. Bộ này bao gồm tổng hợp, định nghĩa xuyên trang, từ khóa thiếu dấu, khái niệm dễ nhầm, ngữ cảnh, nhớ sai, ngoài nguồn và kiểm tra trích dẫn. Chạy đủ 144 lượt trước khi kết luận hệ thống dùng tốt cho toàn sách; bộ nhanh không thay thế độ phủ các chương.

**Ví dụ ngưỡng nội bộ để bắt đầu:** ít nhất 85% lượt có điểm chuẩn hóa từ 80 trở lên; độ chính xác trích dẫn ít nhất 95%; tỷ lệ hiểu đúng tham chiếu ít nhất 90%. Đây là gợi ý ban đầu, cần hiệu chỉnh theo yêu cầu sản phẩm và chi phí chấp nhận lỗi.

Đặt **nguồn giả và nguyên văn bịa là lỗi chặn nghiệm thu**, dù điểm trung bình cao. Một lần quan sát không có lỗi trong bộ test chỉ chứng minh không thấy lỗi trong mẫu này, không chứng minh hệ thống không bao giờ bịa. Không dùng điểm trung bình để che session yếu: báo điểm theo nhóm, từng session và các lỗi nghiêm trọng.

Để lập nguồn chuẩn chi tiết hơn, người chấm nên chọn một hoặc nhiều đoạn cụ thể cho từng ý cần đạt và lưu nguyên văn cùng trang. Các vùng trang trong tài liệu này đã được đối chiếu với cấu trúc và nội dung PDF, nhưng không thay thế bước gán evidence chuẩn theo đoạn khi cần benchmark tự động chặt chẽ.

**Mẫu kết luận sau khi chạy:** Hệ thống mạnh ở [nhóm câu] với [số liệu], yếu ở [nhóm câu] với [số liệu]. Lỗi chính nằm ở [giai đoạn đã được log/đối chứng xác nhận]. Các vấn đề ưu tiên sửa là [lỗi nghiêm trọng hoặc phổ biến]. Những phần chưa thể kết luận là [không có log, không đủ mẫu, chưa chạy tải, hoặc chưa kiểm tra tài liệu khác].

## 11 Phạm vi và nguồn đối chiếu

Nguồn duy nhất để xây dựng các kỳ vọng nội dung là PDF người dùng cung cấp: Giáo trình Triết học Mác - Lê Nin (2)(1).pdf, 214 trang, hai phần và 14 chương. Các kịch bản sinh viên, ví dụ vận dụng, thang điểm, đối chứng và ngưỡng nghiệm thu là thiết kế của bộ kiểm thử, không phải chỉ dẫn của giáo trình.

Bộ này đánh giá RAG hội thoại với một cuốn sách. Chưa đánh giá chọn nguồn giữa nhiều sách, quyền truy cập, tài liệu cập nhật, tấn công chèn chỉ dẫn vào tài liệu, hoặc tải đồng thời nhiều người. Muốn kết luận về các mặt đó cần bộ dữ liệu và phép thử bổ sung. Bộ câu hỏi cũng không thay thế kiểm tra việc extraction/OCR đã giữ đúng chữ, công thức, chú thích và thứ tự trang.
