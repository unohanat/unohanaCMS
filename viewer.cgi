#!/usr/bin/perl

#--------------------
# うのはなCMS
# 制作：うのはな透
# 使用は自己責任で
#--------------------

#設定
#１ページに表示する件数を指定
$article_per_page = 5;
#設定ファイルがあるディレクトリ
$data_dir = "_data/";
#記事があるディレクトリ
$article_dir = "_archive/";
#コメントがあるディレクトリ
$comment_dir = "_comment/";


use Encode;
use Time::Local qw(timelocal);

print "Content-type: text/html; charset=shift-jis\n\n";

#ブログ用の引数
#表示モード（page,archive,category,date）
#パラメータ（category,dateのみ）
#ID（archiveなら記事ID、page,category,dateならページID）

#デフォルト値の設定
$mode = "page";
$id = 1;

#GETメソッドで受け取り
if($ARGV[0]){ $mode = $ARGV[0]; }
if($mode eq "category" || $mode eq "date"){
  $param = $ARGV[1];
  if($ARGV[2]){ $id = $ARGV[2]; }
}else{
  if($ARGV[1]){ $id = $ARGV[1]; }
}

#POSTメソッドで引数を渡されたら、コメント投稿をする
read (STDIN, $PostData, $ENV{'CONTENT_LENGTH'});
if($PostData){
  &post_comment($PostData,$id);
}

#ページを表示する
print &make_page($mode,$param,$id);



#以下サブルーチン

#ページを表示する
sub make_page {
  local($mode) = $_[0];
  local($param) = $_[1];
  local($id) = $_[2];
  local($text);
  
  #記事を生成する
  local(@article_list);
  if($mode ne "archive"){
    @article_list = &get_article_list($mode,$param,$id);
    foreach $x (@article_list){
      $text .= &make_article("partial",$x);
    }
  }else{
    $text = &make_article("full",$id);
  }
  
  my $file = $data_dir."master.dat";
  if(&if_browsing_from_smartphone()){ $file = $data_dir."master_mobile.dat"; }
  open(IN,$file);
  @master = <IN>;
  close(IN);

  my $neighbor = &make_neighbor_navi($mode,$param,$id);
  
  #master.datの必要な部分を置換する
  foreach $x (@master){
    if($x =~ /__pagetitle__/){
      if($mode ne "archive"){
        $x =~ s/__pagetitle__//;
      }else{
        $x =~ s/__pagetitle__/$article_title - /;
      }
    }
    $x =~ s/__noticearticle__/&make_notice()/e;
    $x =~ s/__neighbornavi__/$neighbor/;
    $x =~ s/__eacharticle__/$text/;
    $x =~ s/__currenturl__/$ENV{'REQUEST_URI'}/g;
    $x =~ s/__lastarticle__/&make_last_article()/e;
    $x =~ s/__lastcomment__/&make_last_comment()/e;
    $x =~ s/__categorylist__/&make_category_list()/e;
    $x =~ s/__montharchive__/&make_month_list()/e;
    
  }
  
  return(@master);
}

#どの記事を表示するか調べる
sub get_article_list {
  local($mode) = $_[0];
  local($param) = $_[1];
  local($id) = $_[2];
  
  my $file;
  if($mode eq "category"){
    $file = "category_log.dat";
  }else{
    $file = "article_log.dat";
  }
  
  local(@article_list);
  open(IN,$file);
  local(@text) = <IN>;
  close(IN);
  
  local($count);
  local($i);
  local($hit);
  local($max);
  #最大件数を調べる
  if($mode eq "page"){
    $max = &get_article_count("all");
  }else{
    $max = &get_article_count($param);
  }
  $hit=0;
  if($mode eq "page"){
    #総覧の場合
    foreach $x (@text){
      if($x =~ /(\d+)-(\d+)/){ next; }
      $x =~ s/\n|\r//g;
      if($count >= $article_per_page*($id-1)){
        $article_list[$i] = $x;
        $i++;
      }
      $count++;
      if($i>=$article_per_page || $count>=$max){ last; }
    }
  }else{
    #カテゴリ別・月別場合
    foreach $x (@text){
      #とりあえずパラメータ（XX年YY月など）にヒットするまで回す
      $x =~ s/\n|\r//g;
      if($x eq &url_decode($param)){
        $hit = 1;
        next;
      }
      if(!$hit){ next; }
      #パラメータにヒットしたら読み始める。ただし次のパラメータが来たら終了
      if($x !~ /^\d+$/){ last; }
      if($count >= $article_per_page*($id-1)){
        $article_list[$i] = $x;
        $i++;
      }
      $count++;
      if($i>=$article_per_page || $count>=$max){ last; }
    }
  }
  
  return(@article_list);
}

#記事を生成する
#引数は(mode,id)．modeはfull or partial
sub make_article {
  local($mode) = $_[0];
  local($id) = $_[1];
  local($content) = &make_article_content($mode,$id);
  local($comment_count) = &count_comment($id);
  local($full_text);
  
  my $file = $data_dir."each_article.dat";
  open(IN,$file);
  local(@text) = <IN>;
  close(IN);
  
  local($article_category_url) = &url_encode($article_category);
  foreach $x (@text){
    $x =~ s/__articleid__/$id/g;
    $x =~ s/__articledate__/$article_date/g;
    $x =~ s/__articledate2__/$article_date2/g;
    $x =~ s/__articletitle__/$article_title/g;
    $x =~ s/__articlecontent__/$content/;
    $x =~ s/__articlecategory__/$article_category/g;
    $x =~ s/__articlecategoryurl__/$article_category_url/g;
    $x =~ s/__commentcount__/$comment_count/;
    if($x =~ /__commentform__/){
      if($mode eq "full"){
        $x = &make_comment_form($id);
      }else{
        $x = "";
      }
    }
    $full_text .= $x;
  }
  return($full_text);
}

#記事本文をtxtから生成する
#引数は(mode,id)．modeはfull or partial
sub make_article_content{
  local($mode) = $_[0];
  local($id) = $_[1];
  local($full_text);
  local($if_p);local($if_ul);local($if_pre);local($if_code) = 0;
  local($img_count) = 1;
  
  $file = $article_dir.$id.".txt";
  open(IN,$file);
  local(@text) = <IN>;
  close(IN);
  
  foreach $x (@text){
    #行全体に対する処理
    if($x =~ /^(date|title|category):(.+)$/){
      #メタデータ読み込み
      if($1 eq "date"){
        $article_date = $2;
        $article_date2 = $article_date;
        $article_date2 =~ s/(\d+)-(\d+)-(\d+)/$1年$2月$3日/;
      }elsif($1 eq "title"){
        $article_title = $2;
      }else{
        $article_category = $2;
      }
      next;
    }elsif($x =~ /^\*(.+)$/){
      #見出し表示
      $x = "<h3>".$1."</h3>\n";
    }elsif($x =~ /^-(.+)$/){
      #リスト表示
      $x = "<li>".$1."</li>\n";
      if(!$if_ul){
        $if_ul = 1;
        $x = "<ul>\n".$x;
      }
    }elsif($x =~ /^\s*$/){
      #空行は段落・リストを終了させる
      if($if_p){
        $if_p = 0;
        $x = "</p>\n";
      }elsif($if_ul){
        $if_ul = 0;
        $x = "</ul>\n";
      }
    }elsif($x =~ /^=====$/){
      #続きを読む表示
      if($mode eq "full"){
        $x = "";
      }else{
        #パーマネントページ以外なら、ここで打ち切り
        $x = "<a href=\"/archive/$id\">続きを読む</a>\n";
        $full_text .= $x;
        last;
      }
    }elsif($x =~ /<(\/)?pre>/){
      if($x =~ /<(\/)?pre>/){
        #preタグ内かを判別（<br>を付加しない）
        $if_pre++;
        $if_pre%=2;
      }
    }elsif(!$if_pre){
      #段落表示
      $x =~ s/\n/<br>\n/g;
      if(!$if_p){
        $if_p = 1;
        $x = "<p>\n".$x;
      }
    }
    #行内に対する処理
    #a,img系処理
    if($x =~ /\[\[img\|(.*?)\]\]/){
      $x =~ s/\[\[img\|(.*?)\]\]/<img src="\/img\/$id-$img_count" alt="$1">/g;
      $img_count++;
    }
    $x =~ s/\[\[(.*?)\|(.*?)\]\]/<a href="$2">$1<\/a>/g;
    #em,strong系処理
    $x =~ s/\{\{\{\{(.*?)\}\}\}\}/<strong>$1<\/strong>/g;
    $x =~ s/\{\{\{(.*?)\}\}\}/<em>$1<\/em>/g;
    $x =~ s/\{\{(.*?)\}\}/<em class="psst">$1<\/em>/g;
    #full_textに追加
    $full_text .= $x;
  }
  
  #行間にまたがる処理
  if($if_p){
    $full_text .= "</p>\n";
  }elsif($if_ul){
    $full_text .= "</ul>\n";
  }
  $full_text =~ s/<br>\n<\/p>/\n<\/p>/g;
  return($full_text);
}

#指定されたIDの記事のコメント数を数える
sub count_comment {
  local($id) = $_[0];
  local($count) = 0;
  
  $file = $comment_dir.$id.".txt";
  if(-e $file && -s $file){
    open(IN,$file);
    while(<IN>){
      if($_ =~ /^end_comment$/){ $count++; }
    }
    close(IN);
  }
  
  return($count);
}

#指定されたIDの記事の、コメントと投稿欄を表示する
sub make_comment_form {
  local($id) = $_[0];
  local($full_text);
  local($comment) = &make_each_comment($id);
  
  my $file = $data_dir."comment.dat";
  open(IN,$file);
  while($x = <IN>){
    $x =~ s/__eachcomment__/$comment/;
    $x =~ s/__articleid__/$id/;
    $full_text .= $x;
  }
  close(IN);
  
  return($full_text);
}

#指定されたIDのコメントログから、それぞれのコメントを生成する
sub make_each_comment{
  local($id) = $_[0];
  local($full_text);
  local($count) = 1;
  my $file = $comment_dir.$id.".txt";
  if(-e $file && -s $file){
    open(IN,$file);
    local(@text) = <IN>;
    close(IN);
    $file = $data_dir."each_comment.dat";
    open(IN,$file);
    local(@format) = <IN>;
    close(IN);
    $comment_message = "";
    $comment_mail = "";
    $comment_url = "";
    
    foreach $x (@text){
      if($x =~ /^_(name|date|mail|url|ip):(.+)$/){
        #メタデータ
        if($1 eq "name"){
          $comment_name = $2;
        }elsif($1 eq "date"){
          $comment_date = $2;
          $comment_date2 = $comment_date;
          $comment_date2 =~ s/(\d+)-(\d+)-(\d+)T(.*)\+09:00/$1年$2月$3日 $4/;
        }elsif($1 eq "mail"){
          $comment_mail = $2;
        }elsif($1 eq "url"){
          $comment_url = $2;
        }
      }elsif($x =~ /^end_comment$/){
        #コメントの終わりなので、一旦データを出力する
        local(@temp) = @format;
        foreach $y (@temp){
          $y =~ s/__commentnumber__/$count/g;
          $y =~ s/__commentmessage__/$comment_message/g;
          $y =~ s/__commentname__/$comment_name/g;
          $y =~ s/__commentdate__/$comment_date/g;
          $y =~ s/__commentdate2__/$comment_date2/g;
          if($y =~ /__commentmail__/){
            if($comment_mail){
              $y =~ s/__commentmail__/$comment_mail/;
            }else{ $y = ""; }
          }elsif($y =~ /__commenturl__/){
            if($comment_url){
              $y =~ s/__commenturl__/$comment_url/g;
            }else{ $y = ""; }
          }
          $full_text .= $y;
        }
        #メタデータのリセット
        $comment_message = "";
        $comment_mail = "";
        $comment_url = "";
        $count++;
      }else{
        #本文に読み込み
        $x =~ s/\n|\r//g;
        $x =~ s/$/<br>\n/;
        $comment_message .= $x;
      }
    }
  }else{
    $full_text = "<p>コメントはありません。</p>\n";
  }
  
  $full_text =~ s/<br>\n(\s*)<\/p>/$1<\/p>/g;
  return($full_text);
}

#(mode,param,id)から両隣のページを調べ、ナビを表示する
sub make_neighbor_navi {
  local($mode) = $_[0];
  local($param) = $_[1];
  local($id) = $_[2];
  local($full_text);
  local($hit);
  $next = 0;
  $prev = 0;
  
  if($mode eq "archive"){
    #パーマネントページの場合
    open(IN,"article_log.dat");
    while($x = <IN>){
      if($x =~ /(\d+)-(\d+)/){ next; }
      $now = $x;
      $now =~ s/\n|\r//g;
      if($now == $id){
        $hit = 1;
      }elsif($hit){
        $prev = $now;
        last;
      }
      if(!$hit){ $next = $now; }
    }
    close(IN);
    if($next){ $nexturl = "/archive/".$next; }
    if($prev){ $prevurl = "/archive/".$prev; }
  }else{
    #パーマネントページ以外の場合
    if($mode eq "page"){
      $article_count = &get_article_count("all");
    }else{
      $article_count = &get_article_count($param);
    }
    $next = $id - 1;
    $prev = $id + 1;
    if($next){
      if($mode eq "page"){
        $nexturl = "page/".$next;
      }elsif($mode eq "date"){
        $nexturl = "date/".$param."/".$next;
      }else{
        $nexturl = $mode."/".&url_encode($param)."/".$next;
      }
    }
    $max_count = ($prev-1)*$article_per_page;
    if($max_count < $article_count){
      if($mode eq "page"){
        $prevurl = "page/".$prev;
      }elsif($mode eq "date"){
        $prevurl = "date/".$param."/".$prev;
      }else{
        $prevurl = $mode."/".&url_encode($param)."/".$prev;
      }
    }else{ $prev = 0; }
    if($next==1 && $mode eq "page"){ $nexturl = "/"; }
  }
  
  if($mode eq "archive"){
    $next_title = &get_article_title($next);
    $prev_title = &get_article_title($prev);
  }else{
    $next_title = "新しい".$article_per_page."件";
    $prev_title = "過去の".$article_per_page."件";
  }
  
  #フォーマットファイルを開き置換
  my $file = $data_dir."neighbor_navi.dat";
  open(IN,$file);
  while(<IN>){
    if($_ =~ /__nextid__/){
      if($next){
        $_ =~ s/__nextid__/$nexturl/;
        $_ =~ s/__nexttitle__/$next_title/;
        if(!$prev){ $_ =~ s/ \| //; }
      }else{
        $_ = "";
      }
    }elsif($_ =~ /__previd__/){
      if($prev){
        $_ =~ s/__previd__/$prevurl/;
        $_ =~ s/__prevtitle__/$prev_title/;
      }else{
        $_ = "";
      }
    }
    $full_text .= $_;
  }
  close(IN);
  
  return($full_text);
}

#指定されたIDの記事のタイトルを得る
sub get_article_title {
  local($id) = $_[0];
  local($title);
  
  if(!$id){ return(""); }
  $file = $article_dir.$id.".txt";
  open(IN,$file);
  while(<IN>){
    if($_ =~ /^title:(.*)$/){
      $title = $1;
      last;
    }
  }
  close(IN);
  return($title);
}

#指定されたIDの記事の投稿日時を得る
sub get_article_date {
  local($id) = $_[0];
  local($date);
  
  if(!$id){ return(""); }
  $file = $article_dir.$id.".txt";
  open(IN,$file);
  while(<IN>){
    if($_ =~ /^date:\d+-(\d+)-(\d+)/){
      $date = $1."/".$2;
      last;
    }
  }
  close(IN);
  return($date);
}

#指定されたIDの記事のn番目のコメントの投稿者名を得る
sub get_comment_name {
  local($id) = $_[0];
  local($num) = $_[1];
  local($name);
  local($count) = 1;
  
  $file = $comment_dir.$id.".txt";
  open(IN,$file);
  while(<IN>){
    if($_ =~ /^end_comment$/){ $count++; }
    if($_ =~ /^_name:(.*)$/){
      if($count==$num){ $name = $1; last; }
    }
  }
  close(IN);
  
  return($name);
}

#指定されたIDの記事のn番目のコメントの投稿日時を得る
sub get_comment_date {
  local($id) = $_[0];
  local($num) = $_[1];
  local($date);
  local($count) = 1;
  
  $file = $comment_dir.$id.".txt";
  open(IN,$file);
  while(<IN>){
    if($_ =~ /^end_comment$/){ $count++; }
    if($_ =~ /^_date:\d+-(\d+)-(\d+)/){
      if($count==$num){ $date = $1."/".$2; last; }
    }
  }
  close(IN);
  
  return($date);
}


#指定された区分の記事の数を得る
sub get_article_count {
  local($param) = $_[0];
  local($count) = 0;
  if($param eq "all"){
    #記事総数
    open(IN,"article_log.dat");
    while(<IN>){
      if($_ !~ /\d+-\d+/){ $count++; }
    }
    close(IN);
  }elsif($param =~ /^(\d+)-(\d+)$/){
    #月別記事数
    open(IN,"article_log.dat");
    while(<IN>){
      $_ =~ s/\n|\r//g;
      if($_ eq $param){ $hit = 1; next; }
      elsif($_ =~ /\d+-\d+/){ if($hit){ last; } next; }
      if($hit){ $count++; }
    }
  }else{
    #カテゴリ別記事数
    open(IN,"category_log.dat");
    while(<IN>){
      $_ =~ s/\n|\r//g;
      if($_ eq &url_decode($param)){ $hit = 1; next; }
      elsif($_ !~ /^\d+$/){ if($hit){ last; } next; }
      if($hit){ $count++; }
    }
  }
  return($count);
}

#最新n件の記事を表示する
sub make_last_article {
  local($full_text);
  local($format);
  local($title);local($date);
  local($temp);
  
  my $file = $data_dir."last_article.dat";
  open(IN,$file);
  while(<IN>){ $format .= $_; };
  close(IN);
  
  local(@article_list) = &get_article_list("page","",1);
  
  foreach $x (@article_list){
    $title = &get_article_title($x);
    $date = &get_article_date($x);
    $temp = $format;
    $temp =~ s/__articledate__/$date/;
    $temp =~ s/__articleid__/$x/;
    $temp =~ s/__articletitle__/$title/;
    $full_text .= $temp;
  }
  
  return($full_text);
}

#最新n件のコメントを表示する
sub make_last_comment {
  local($full_text);
  local($format);
  local(@article_list);
  local(@number_list);
  
  my $file = $data_dir."last_comment.dat";
  open(IN,$file);
  while(<IN>){ $format .= $_; }
  close(IN);
  
  local($i);
  if(!(-e "comment_log.dat")){ return("<li>コメントはありません</li>\n"); }
  open(IN,"comment_log.dat");
  while(<IN>){
    if($_ = /^(\d+)-(\d+)$/){
      $article_list[$i] = $1;
      $number_list[$i] = $2;
      $i++;
    }
    if($i>=$article_per_page){ last; }
  }
  close(IN);
  for($i=0; $i<=$#article_list; $i++){
    $title = &get_article_title($article_list[$i]);
    $date = &get_comment_date($article_list[$i],$number_list[$i]);
    $name = &get_comment_name($article_list[$i],$number_list[$i]);
    $temp = $format;
    $temp =~ s/__commentdate__/$date/;
    $temp =~ s/__commentname__/$name/;
    $temp =~ s/__articleid__/$article_list[$i]/;
    $temp =~ s/__articletitle__/$title/;
    $full_text .= $temp;
  }
  
  return($full_text);
}

#カテゴリーリストを表示する
sub make_category_list {
  return &make_archive_list("category");
}

#月別リストを表示する
sub make_month_list {
  return &make_archive_list("date");
}

#カテゴリ(category)or月別(date)リストを表示する
sub make_archive_list {
  my $mode = $_[0];
  my $file;
  if($mode eq "category"){ $file = "category_log.dat"; }else{ $file = "article_log.dat"; }
  my $text;
  my $value;
  my $url;
  my $count;
  if(!(-e $file)){ return ""; }
  open(IN,$file);
  while(<IN>){
    $_ =~ s/\n|\r//g;
    if($_ !~ /^\d+$/){
      if($value){ $text .= "($count)</a></li>\n"; }
      $count = 0;
      $value = $_;
      if($mode eq "date"){
        $url = $value;
        $value =~ s/(\d+)-(\d+)/$1年$2月/;
      }else{
        $url = &url_encode($value);
      }
      $text .= "<li><a href=\"/$mode/$url\">$value";
    }else{
      $count++;
    }
  }
  $text .= "($count)</a></li>\n";
  close(IN);
  return $text;
}

#URLエンコードする
sub url_encode {
  local($str) = $_[0];
  $str =~ s/([^\w ])/'%'.unpack('H2', $1)/ego;
  $str =~ tr/ /+/;
  return($str);
}

#URLデコードする
sub url_decode {
  local($str) = $_[0];
  $str =~ tr/+/ /;
  $str =~ s/%([0-9A-Fa-f][0-9A-Fa-f])/pack('H2', $1)/ego;
  $str =~ s/^プログラ.*ング$/プログラミング/;
  $str =~ s/^フェ.*$/フェチ/;
  $str =~ s/^ゲ.*ム$/ゲーム/;
  return($str);
}

#コメントを投稿する（旧verのまま）
#$_[0]はPOSTの文字列まるまる、$_[1]は記事ID
sub post_comment {
  local($id) = $_[1];
  local(@tmp);
  local($year);local($month);
  local(@indata) = split (/&/,$_[0]); #受け取ったデータを&で区切り、配列へ
  foreach $tmp (@indata) #フォームの要素分（配列分）以下の処理を繰り返す
  {
    ($name_,$value_) = split (/=/,$tmp); # =記号で区切り、名前と値に分ける
    $value_ =~ s/%([a-fA-F0-9][a-fA-F0-9])/pack('H2', $1)/ego; #MIME文字デコード
    $in{$name_} = $value_; #区切った名前を付けた連想配列に値を入れる
  }
  # 欄が空だったり、禁止ワードが入っていたら弾く
  if(!$in{'name'} or !$in{'mes'}){ return; }
  $in{'mes'} =~ s/<.*?>//g;
  $in{'name'} =~ s/<.*?>//g;
  $in{'mes'} =~ s/\+/ /g;
  $in{'name'} =~ s/\+/ /g;
  if($in{'mes'} =~ /wget|http:\/\//){ return; }
  # 指定以上の文字数は弾く
  if(length($in{'name'}) > 30 or length($in{'mes'}) > 1000){ return; }
  # 重複投稿は弾く
  local($last_comment);local($if_comment);
  open(IN,"_comment/".$id.".txt");
  while(<IN>){
    if($_ =~ /end_comment/){
      $if_comment = 0;
    }elsif($_ !~ /_(name|date|mail|url):(.*)$/){
      if(!$if_comment){
        $last_comment = $_;
        $if_comment = 1;
      }else{
        $last_comment .= $_;
      }
    }
  }
  $last_comment =~ s/\n$//;
  close(IN);
  if($last_comment eq $in{'mes'}){ return; }
  # 以下、投稿処理
  ($tmp[0],$tmp[1],$tmp[2],$tmp[3],$tmp[4],$tmp[5],$tmp[6]) = localtime(time());
  open(OUT,">> _comment/".$id.".txt");
  flock(OUT,2);
  print(OUT $in{'mes'}."\n");
  print(OUT "_name:".$in{'name'}."\n");
  print(OUT "_date:".($tmp[5]+1900)."-".&zeroadd($tmp[4]+1)."-".&zeroadd($tmp[3])."T".&zeroadd($tmp[2]).":".&zeroadd($tmp[1])."+09:00\n");
  if($in{'email'}){ print(OUT "_mail:".$in{'email'}."\n"); }
  if($in{'url'}){ print(OUT "_url:".$in{'url'}."\n"); }
  print(OUT "_ip:".$ENV{'REMOTE_ADDR'}."\n");
  print(OUT "end_comment\n");
  close(OUT);
  
  #コメントログにコメント履歴を出力
  local($count) = &count_comment($id);
  local($comment_log);
  open(IN,"comment_log.dat");
  for($i=0;$i<$article_per_page-1;$i++){
    if($_ = <IN>){
      $comment_log .= $_;
    }else{ last; }
  }
  $comment_log = $id."-".$count."\n".$comment_log;
  close(IN);
  open(OUT,"> comment_log.dat");
  print(OUT $comment_log);
  close(OUT);
}

#おしらせを表示する
sub make_notice {
  my $text;
  my $file = $data_dir."notice_article.dat";
  if(!(-e $file)){ return ""; }
  open(IN,$file);
  while(<IN>){ $text .= $_; }
  close(IN);
  return $text;
}

#数字を渡すと"0X"形式にしてくれる（二桁）
sub zeroadd {
  #文字列から数値にするための無駄な操作。
  #これにより有効な数字は1桁か2桁しかなくなる。
  $_[0]++;
  $_[0]--;
  if(length($_[0])==1){
    return "0".$_[0];
  }elsif(length($_[0])==2){
    return $_[0];
  }else{
    return "01";
  }
}

#スマートフォンからの接続か調べる
sub if_browsing_from_smartphone {
if ($ENV{'HTTP_USER_AGENT'} =~ m/android.+mobile|avantgo|bada\/|blackberry|blazer|compal|elaine|fennec|hiptop|iemobile|ip(hone|od)|iris|kindle|lge |maemo|midp|mmp|netfront|opera m(ob|in)i|palm( os)?|phone|p(ixi|re)\/|plucker|pocket|psp|symbian|treo|up\.(browser|link)|vodafone|wap|windows (ce|phone)|xda|xiino/i || substr($ENV{'HTTP_USER_AGENT'}, 0, 4) =~ m/1207|6310|6590|3gso|4thp|50[1-6]i|770s|802s|a wa|abac|ac(er|oo|s\-)|ai(ko|rn)|al(av|ca|co)|amoi|an(ex|ny|yw)|aptu|ar(ch|go)|as(te|us)|attw|au(di|\-m|r |s )|avan|be(ck|ll|nq)|bi(lb|rd)|bl(ac|az)|br(e|v)w|bumb|bw\-(n|u)|c55\/|capi|ccwa|cdm\-|cell|chtm|cldc|cmd\-|co(mp|nd)|craw|da(it|ll|ng)|dbte|dc\-s|devi|dica|dmob|do(c|p)o|ds(12|\-d)|el(49|ai)|em(l2|ul)|er(ic|k0)|esl8|ez([4-7]0|os|wa|ze)|fetc|fly(\-|_)|g1 u|g560|gene|gf\-5|g\-mo|go(\.w|od)|gr(ad|un)|haie|hcit|hd\-(m|p|t)|hei\-|hi(pt|ta)|hp( i|ip)|hs\-c|ht(c(\-| |_|a|g|p|s|t)|tp)|hu(aw|tc)|i\-(20|go|ma)|i230|iac( |\-|\/)|ibro|idea|ig01|ikom|im1k|inno|ipaq|iris|ja(t|v)a|jbro|jemu|jigs|kddi|keji|kgt( |\/)|klon|kpt |kwc\-|kyo(c|k)|le(no|xi)|lg( g|\/(k|l|u)|50|54|e\-|e\/|\-[a-w])|libw|lynx|m1\-w|m3ga|m50\/|ma(te|ui|xo)|mc(01|21|ca)|m\-cr|me(di|rc|ri)|mi(o8|oa|ts)|mmef|mo(01|02|bi|de|do|t(\-| |o|v)|zz)|mt(50|p1|v )|mwbp|mywa|n10[0-2]|n20[2-3]|n30(0|2)|n50(0|2|5)|n7(0(0|1)|10)|ne((c|m)\-|on|tf|wf|wg|wt)|nok(6|i)|nzph|o2im|op(ti|wv)|oran|owg1|p800|pan(a|d|t)|pdxg|pg(13|\-([1-8]|c))|phil|pire|pl(ay|uc)|pn\-2|po(ck|rt|se)|prox|psio|pt\-g|qa\-a|qc(07|12|21|32|60|\-[2-7]|i\-)|qtek|r380|r600|raks|rim9|ro(ve|zo)|s55\/|sa(ge|ma|mm|ms|ny|va)|sc(01|h\-|oo|p\-)|sdk\/|se(c(\-|0|1)|47|mc|nd|ri)|sgh\-|shar|sie(\-|m)|sk\-0|sl(45|id)|sm(al|ar|b3|it|t5)|so(ft|ny)|sp(01|h\-|v\-|v )|sy(01|mb)|t2(18|50)|t6(00|10|18)|ta(gt|lk)|tcl\-|tdg\-|tel(i|m)|tim\-|t\-mo|to(pl|sh)|ts(70|m\-|m3|m5)|tx\-9|up(\.b|g1|si)|utst|v400|v750|veri|vi(rg|te)|vk(40|5[0-3]|\-v)|vm40|voda|vulc|vx(52|53|60|61|70|80|81|83|85|98)|w3c(\-| )|webc|whit|wi(g |nc|nw)|wmlb|wonu|x700|xda(\-|2|g)|yas\-|your|zeto|zte\-/i) {
  return 1;
}
return 0;
}