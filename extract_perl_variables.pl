#!/usr/bin/env perl
use strict;
use warnings;
use JSON;
use Data::Dumper;
use B::Deparse;
use Scalar::Util qw(reftype refaddr blessed);

# JSONエンコード用の設定
local $Data::Dumper::Indent = 1;
local $Data::Dumper::Sortkeys = 1;
local $Data::Dumper::Terse = 1;

# コマンドライン引数からファイルパスを取得
my $file_path = shift @ARGV or die "Usage: $0 /path/to/perl/file.pl\n";
my $package_name = 'main'; # デフォルトのパッケージ名

# ファイルが存在するか確認
unless (-f $file_path) {
    die "ファイル '$file_path' が見つかりません\n";
}

# ファイルを読み込む（requireではなくdoを使用）
{
    # ファイル内の変数を正しく取得するため、暫定的にstrict/warningsを無効化
    no strict;
    no warnings;
    
    # ファイルを実行（ファイル内の変数がグローバルスコープに展開される）
    do $file_path;
    if ($@) {
        warn "ファイルの実行中にエラーが発生しました: $@\n";
    }
}

# 結果格納用ハッシュ
my %result;

$result{file} = {
    path => $file_path,
    package => $package_name,
};

# シンボルテーブルを取得
my $package_symtab = do {
    no strict 'refs';
    \%{"${package_name}::"};
};

# 変数とサブルーチンを収集
$result{variables} = collect_variables($package_symtab, $package_name);
$result{subroutines} = collect_subroutines($package_symtab, $package_name);
$result{dependencies} = collect_dependencies();

# 結果をJSON形式で出力
print encode_json(\%result);

# 変数を収集する関数
sub collect_variables {
    my ($symtab, $package) = @_;
    my %vars;
    
    foreach my $name (sort keys %$symtab) {
        next if $name =~ /::$/;  # サブパッケージをスキップ
        next if $name =~ /^_</;  # ファイルハンドルをスキップ
        
        my $full_name = "${package}::${name}";
        
        # スカラー変数
        if (defined *{$symtab->{$name}}{SCALAR} && *{$symtab->{$name}}{SCALAR} != \undef) {
            no strict 'refs';
            my $value = ${*{$full_name}};
            $vars{"$name (scalar)"} = {
                type => 'SCALAR',
                value => scalar_to_string($value),
            };
        }
        
        # 配列変数
        if (defined *{$symtab->{$name}}{ARRAY}) {
            no strict 'refs';
            my @array = @{*{$full_name}};
            $vars{"$name (array)"} = {
                type => 'ARRAY',
                value => \@array,
                size => scalar(@array),
            };
        }
        
        # ハッシュ変数
        if (defined *{$symtab->{$name}}{HASH}) {
            no strict 'refs';
            my %hash = %{*{$full_name}};
            $vars{"$name (hash)"} = {
                type => 'HASH',
                value => \%hash,
                keys => [sort keys %hash],
            };
        }
    }
    
    return \%vars;
}

# サブルーチンを収集する関数
sub collect_subroutines {
    my ($symtab, $package) = @_;
    my %subs;
    
    foreach my $name (sort keys %$symtab) {
        next if $name =~ /::$/;  # サブパッケージをスキップ
        next if $name =~ /^_</;  # ファイルハンドルをスキップ
        
        if (defined *{$symtab->{$name}}{CODE}) {
            my $full_name = "${package}::${name}";
            no strict 'refs';
            
            my $deparser = B::Deparse->new();
            my $code = eval { $deparser->coderef2text(\&{$full_name}) };
            
            $subs{$name} = {
                type => 'CODE',
                source => $code || "# Deparse failed",
            };
        }
    }
    
    return \%subs;
}

# モジュールの依存関係を収集する関数
sub collect_dependencies {
    my @deps;
    
    # %INCからロードされたモジュールを取得
    foreach my $inc_key (sort keys %INC) {
        push @deps, {
            name => $inc_key,
            file => $INC{$inc_key},
        };
    }
    
    return \@deps;
}

# スカラー値を文字列に変換する関数
sub scalar_to_string {
    my ($value) = @_;
    
    return "undef" unless defined $value;
    
    if (ref $value) {
        if (blessed($value)) {
            return "OBJECT(" . ref($value) . ")";
        }
        
        my $reftype = reftype($value) || "";
        if ($reftype eq "ARRAY") {
            return "ARRAY(" . scalar(@$value) . " elements)";
        }
        elsif ($reftype eq "HASH") {
            return "HASH(" . scalar(keys %$value) . " keys)";
        }
        else {
            return "$reftype(...)";
        }
    }
    
    # 数値かどうかの確認
    if ($value =~ /^-?\d+(\.\d+)?$/) {
        return $value;
    }
    
    # 文字列として返す
    return $value;
}
