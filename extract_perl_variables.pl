#!/usr/bin/env perl
use strict;
use warnings;
use Data::Dumper;
use B::Deparse;
use Scalar::Util qw(reftype blessed);

# JSONエンコード用の設定
local $Data::Dumper::Indent = 1;
local $Data::Dumper::Sortkeys = 1;
local $Data::Dumper::Terse = 1;

# コマンドライン引数からモジュール名を取得
my $module_name = shift @ARGV or die "Usage: $0 ModuleName\n";

# モジュールの読み込みと変数の取得
my %result;
eval "require $module_name";
if ($@) {
    die "モジュール '$module_name' の読み込みに失敗しました: $@\n";
}

# モジュールのファイルパスを取得 (Module::Infoの代わり)
my $filename = $INC{module_to_path($module_name)};

$result{module} = {
    name => $module_name,
    file => $filename,
};

# シンボルテーブルを取得
my $package_symtab = do {
    no strict 'refs';
    \%{"${module_name}::"};
};

# 変数、サブルーチン、定数を収集
$result{variables} = collect_variables($package_symtab, $module_name);
$result{subroutines} = collect_subroutines($package_symtab, $module_name);
$result{dependencies} = collect_dependencies($module_name);

# 結果をJSON形式の代わりにData::Dumperで出力
print to_json(\%result);

# モジュール名からパス名への変換
sub module_to_path {
    my ($module) = @_;
    (my $path = "$module.pm") =~ s{::}{/}g;
    return $path;
}

# 簡易的なJSONエンコード (JSON.pmを使用せず)
sub to_json {
    my ($data) = @_;
    my $json = simple_json_encode($data);
    return $json;
}

# 簡易的なJSONエンコーダ
sub simple_json_encode {
    my ($data) = @_;
    
    if (!defined $data) {
        return 'null';
    }
    elsif (!ref $data) {
        # 数値かどうか確認
        if ($data =~ /^-?\d+(\.\d+)?$/) {
            return $data;
        }
        else {
            # 文字列エスケープ
            $data =~ s/\\/\\\\/g;
            $data =~ s/"/\\"/g;
            $data =~ s/\n/\\n/g;
            $data =~ s/\r/\\r/g;
            $data =~ s/\t/\\t/g;
            return qq("$data");
        }
    }
    elsif (ref $data eq 'ARRAY') {
        my @items = map { simple_json_encode($_) } @$data;
        return '[' . join(',', @items) . ']';
    }
    elsif (ref $data eq 'HASH') {
        my @items;
        foreach my $key (sort keys %$data) {
            my $value = simple_json_encode($data->{$key});
            $key =~ s/\\/\\\\/g;
            $key =~ s/"/\\"/g;
            push @items, qq("$key":$value);
        }
        return '{' . join(',', @items) . '}';
    }
    else {
        # その他の参照型 (ここでは単純に文字列化)
        return qq("$data");
    }
}

# 変数を収集する関数
sub collect_variables {
    my ($symtab, $package) = @_;
    my %vars;
    
    foreach my $name (keys %$symtab) {
        next if $name =~ /::$/;  # サブパッケージをスキップ
        
        my $full_name = "${package}::${name}";
        
        # スカラー変数
        if (defined *{$symtab->{$name}}{SCALAR} && *{$symtab->{$name}}{SCALAR} != \undef) {
            no strict 'refs';
            $vars{"$name (scalar)"} = {
                type => 'SCALAR',
                value => scalar_to_string(${*{$full_name}}),
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
    
    foreach my $name (keys %$symtab) {
        next if $name =~ /::$/;  # サブパッケージをスキップ
        
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
    my ($module) = @_;
    my @deps;
    
    # %INCからロードされたモジュールを取得
    foreach my $inc_key (keys %INC) {
        my $module_path = $inc_key;
        $module_path =~ s/\//::/g;
        $module_path =~ s/\.pm$//;
        push @deps, {
            name => $module_path,
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
